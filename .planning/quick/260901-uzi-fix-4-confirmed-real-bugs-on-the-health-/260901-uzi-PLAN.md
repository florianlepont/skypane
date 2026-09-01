---
phase: quick-260901-uzi
plan: 260901-uzi
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - companion/layout.py
  - companion/pages/health_page.py
  - companion/static/battery-trend.js
  - companion/static/style.css
  - companion/test_status_pages.py
autonomous: true
requirements: [QUICK-260901-uzi]

must_haves:
  truths:
    - "Finding 1's root cause is one declaration, already in the file and already commented: `.dashboard-grid` declares `align-items: start` (style.css, in the `.dashboard-grid` rule), added by 06.6.3 (UXA-06) with the explicit intent that Health's shorter tiles keep their own intrinsic height beside a taller Corroboration tile. The developer has now looked at the shipped result and wants the opposite. This is a DECISION REVERSAL of UXA-06, not the discovery of a bug — the fix restores CSS Grid's default cross-axis stretch, and the reversal is written into the rule's own comment so a future UXA-06-citing edit cannot silently undo it."
    - "That reversal reaches Health and only Health: `dashboard-grid` is emitted from exactly two places in the whole codebase, both in `health_page.py::render()` (the Screen section's single-tile grid and the Server & data three-tile grid). No other page module emits the class. The sibling `align-items: start` inside the `@media (min-width: 960px)` `.dashboard-shell` rule is a DIFFERENT selector doing a different job (D-21's sticky sidebar depends on it) and is not touched."
    - "Finding 2's root cause is `.data-table { min-width: max-content; }` — a deliberate no-crop floor that is correct for every table of short values (History, the unresolved-prefix registry, the battery readings) and wrong for the one table holding prose: the Resolution-statistics Description column carries full sentences from `_SOURCE_ROWS`, whose max-content width is the whole unwrapped sentence, so the table cannot fit its container and `.data-table-wrap`'s `overflow-x: auto` turns into a real 341px horizontal scroll instead of the safety net it was meant to be."
    - "The fix is scoped by an opt-out modifier, never by weakening the shared floor: `layout.data_table()` gains one optional `prose=False` keyword that adds `data-table--prose` to the `<table>`'s class list, and style.css's `.data-table--prose { min-width: 0; }` neutralises the floor for that table alone. Both selectors are single-class (0,1,0) and both match the same element, so SOURCE ORDER is the only thing that decides — `.data-table--prose` must sit after `.data-table` in the file, and a harness check pins that rather than a comment."
    - "`layout.data_table()` has exactly two production call sites, both in `health_page.py` (the battery readings table and the stats table); History and the unresolved-prefix registry hand-roll their own tables. The new keyword defaults to `False`, so the battery readings table and every harness call site are byte-identical before and after."
    - "Finding 3 cannot be fixed server-side alone. `companion/static/battery-trend.js`'s `reveal()` composes the readout text itself (`mv + \" mV — \" + ts`, written through `textContent`), so humanising only the server-seeded string would be reverted by the user's very first hover, tap or arrow-key move. `battery-trend.js` IS edited by this task — a deliberate reversal of quick task 260901-tsa's own \"not edited\" non-goal, which was correct for a pure reposition and is not correct for a format change."
    - "The humanised format is built once, server-side, and shared: one helper returns the `(value, when)` plain-text pair, and that pair drives the seeded readout, each chart point's `<title>` tooltip, each point's `aria-label`, and a new per-point `data-when` attribute. `battery-trend.js` READS `data-when` rather than formatting a timestamp itself — that keeps its own documented charter intact (\"its entire job is reading attributes already present in the DOM and writing one line of text\") and means the relative-time ladder has exactly one implementation, in `layout.relative_age_text()`, not a second copy in JavaScript."
    - "`textContent` remains the only DOM sink in `battery-trend.js`; the one new attribute write is `setAttribute(\"title\", ts)`, which is not an HTML sink. The file still needs no escaping function, so 06.5-RESEARCH.md's ASVS V5 reasoning is unweakened."
    - "The readout keeps its `id` and its `role=\"status\"` live region, so `getElementById` and the Left/Right/Home/End reveal announcements survive. Its class list changes (the `mono` class moves off the `<p>` and onto the value span), which is a known, in-place harness retarget, not a break."
    - "Finding 4's answer is that the type scale is CORRECT and `.stat-tile__value` does NOT change size. 06.6.4 D-09 retired the Display role outright and the design skill records the surviving four sizes (14/16/20/30) as the current contract; resurrecting a fifth size to win one visual comparison would re-break the claim that retirement was made to restore."
    - "What IS wrong in finding 4 is measurable and structural: the Health page renders TWO different structural levels at the identical 20px serif regular — the top-level D-10 section headings (`Screen`, `Server & data`) and the cards nested inside them (`Battery trend`, `Unresolved prefixes`, `Resolution statistics`). A card title inside a section is subordinate to that section's heading but renders as its equal, which flattens the hierarchy and is exactly what makes an ordinary card heading below the grid out-shout the tile value above it."
    - "The fix demotes the nested tier rather than promoting the tile: Health's two migrated cards carry a `page-section--nested` modifier and, together with `.battery-trend-section`'s own heading, render at the Emphasis role (Body size plus semibold) — the same role `.stat-tile__value` already uses, so a card heading and a tile value now read as peers and the section headings above them are unambiguously the top tier. No new size, no new weight, no new token, and the serif family is inherited from `.text-heading` unchanged."
    - "The demotion is scoped by an explicit modifier class emitted only by `health_page.py`, so Settings' `page-section` groups, History's `page-section`, and Health's own top-level source-fault `page-section banner banner--anomaly` block are all untouched — a bare `.page-section h2` rule would have silently resized three other pages."
    - "Finding 5 is investigated and left OPEN, with no speculative CSS shipped. Two source-grounded candidates are recorded by name and line for the developer's own Safari pass: (a) `.data-table th` declares `padding: 0 var(--space-md) 10px` — zero top padding — so a header stuck at the scroll container's `top: 0` has no space above its glyphs and the visible clipping depends on font ascent metrics, which genuinely differ between WebKit and Blink; (b) `.data-table-wrap th { background: var(--color-canvas) }`, which style.css's own comment already pre-registers as never live-validated and wrong-looking for in-card tables. Neither is changed here: (a) would re-space every table header in the app and (b) would fix the in-card tables by breaking History's, which is the only table long enough for the sticky state to reliably engage."
    - "Every value introduced comes from this stylesheet's own token set — `var(--font-body-size)`, `var(--font-label-size)`, `var(--weight-semibold)`, `var(--weight-regular)`, and the existing 70% `color-mix` muted strength. No new custom property, no new size, no new muted strength, no `:has()`."
    - "`companion/test_status_pages.py` passes with `EXPECTED_CHECK_COUNT` moved from its real on-disk baseline to that baseline plus exactly 5, and with every check the four fixes break retargeted IN PLACE (no count change) plus the Section 3 live-HTTP check extended IN PLACE."
    - "`scripts/run-all-tests.sh` reports exactly one failing harness, `server/test_poll_loop.py` (the known, pre-existing, unrelated digest mismatch). No harness that passed before this task fails after it."
    - "A real `companion/app.py` process was started, signed into, and `GET /health` fetched over HTTP with seeded battery data, confirming the stretched grid CSS, the prose-table modifier, the humanised readout and the demoted card headings all reach a genuine response body — not only an in-process `render()` call."
  artifacts:
    - path: "companion/static/style.css"
      provides: "`.dashboard-grid` restored to cross-axis stretch with the UXA-06 reversal documented; `.data-table--prose` placed after `.data-table`; `.page-section--nested > h2, .battery-trend-section > h2` at the Emphasis role; `.battery-readout__detail`; the `.stat-tile__value .mono` rule extended to cover `.battery-readout .mono`"
      contains: ".data-table--prose {"
    - path: "companion/layout.py"
      provides: "`data_table()`'s optional `prose=False` keyword and the reasoning for a table-level opt-out rather than a weakened shared floor"
      contains: "data-table--prose"
    - path: "companion/pages/health_page.py"
      provides: "the humanised `(value, when)` battery-reading helper feeding the readout, the point tooltips and the new `data-when` attribute; `prose=True` on the stats table; `page-section--nested` on both migrated cards"
      contains: "data-when"
    - path: "companion/static/battery-trend.js"
      provides: "`reveal()` writing the humanised value/detail pair read from the DOM, with the pre-`data-when` composition kept as an explicit fallback"
      contains: "data-when"
    - path: "companion/test_status_pages.py"
      provides: "5 new checks, the in-place retargets the four fixes force, the in-place live-HTTP extension, and `EXPECTED_CHECK_COUNT` at on-disk-baseline + 5"
      contains: "data-table--prose"
  key_links:
    - from: "style.css's `.data-table--prose { min-width: 0 }`"
      to: "`.data-table { min-width: max-content }` earlier in the same file — equal (0,1,0) specificity on the same element means source order alone decides which wins; move the modifier above the base rule and finding 2 silently returns, with nothing else in the file to notice"
    - from: "`health_page.py`'s per-point `data-when` attribute"
      to: "`battery-trend.js`'s `reveal()` — the humanised string exists server-side only; without the JS read the first hover overwrites the readout with the raw ISO format again and finding 3 is visually a no-op after one pointer move"
    - from: "`health_page.py`'s `page-section--nested` modifier"
      to: "style.css's `.page-section--nested > h2` rule and `test_status_pages.py`'s existing `'<section class=\"page-section\">'` index/count assertions — the modifier changes that literal, so those checks start measuring the wrong element the moment it ships; retargeting them is part of the same task, not the harness task"
    - from: "`.dashboard-grid`'s restored stretch"
      to: "`_server_data_grid_holds_three_tiles_migrated_cards_outside_grid()` and every rendered-slice check that indexes on grid boundaries — the stretch is CSS-only and changes no markup, which is exactly why it must be pinned by a stylesheet guard rather than assumed covered by the markup checks"
---

<objective>
Fix four confirmed, live-measured bugs on the shipped Health page found when the developer tested it in real Safari immediately after quick task 260901-tsa landed, and investigate a fifth without guessing at it.

| # | Bug | Confirmed root cause | Fix |
|---|-----|----------------------|-----|
| 1 | Server & data's three stat tiles render at wildly uneven heights (measured: 107.7 / 261.8 / 140.4px, same grid row) | `.dashboard-grid` declares `align-items: start`, added by 06.6.3 (UXA-06) with exactly this outcome as its stated intent | Reverse UXA-06: restore CSS Grid's default cross-axis stretch, Health-scoped by construction |
| 2 | Resolution-statistics table forces real horizontal overflow (measured: `scrollWidth` 1172 vs `clientWidth` 831) | `.data-table { min-width: max-content }` — right for short-value tables, wrong for the one column holding full prose sentences, which therefore can never wrap | A `data-table--prose` opt-out modifier on that one table, from one new optional `data_table()` keyword |
| 3 | Battery readout is a raw ISO-8601 timestamp in bold monospace, unlike every other timestamp on the page | `_latest_numeric_battery_label()` interpolates the raw ISO — AND `battery-trend.js` composes the same raw format itself on every hover/tap/arrow | Humanise server-side once, share it via a per-point `data-when` attribute, split value from detail as the validated sketch does, and teach the JS to read it |
| 4 | The tile's headline value reads as less prominent than an ordinary section heading below it | NOT the tile: two structural levels (D-10 section headings and the cards nested inside them) both render at 20px serif regular, flattening the hierarchy | Demote the nested tier to the Emphasis role. `.stat-tile__value` is not touched |
| 5 | Readings-history disclosure header appears half-cut-off in Safari | Not reproducible from source; two named candidates, neither safely fixable blind | Investigate, record both candidates with line references, ship no speculative CSS, leave it open |

Purpose: close the developer's live Safari findings against the page 06.6.4.1's closing checkpoint is still waiting on, and be explicit about the one finding that is not closed.

Output: one stylesheet with five rule changes, one new optional `layout` keyword, three markup/format changes in `health_page.py`, one `reveal()` change in `battery-trend.js`, 5 new harness checks plus in-place retargets, and a SUMMARY that names what still needs live-browser pixel confirmation.

**Approach note — two of these findings reverse a prior decision, and both reversals must be written down where the next reader will trip over them.** Finding 1 reverses 06.6.3's UXA-06 (`align-items: start` was added deliberately, with a comment saying so). Finding 3 reverses quick task 260901-tsa's own explicit non-goal ("`companion/static/battery-trend.js`. Not edited."), which was correct for a pure reposition and is not correct once the readout's FORMAT changes, because that file builds the format itself. Neither reversal is a correction of a mistake; both are the developer looking at the shipped result and asking for the other option. Record them as such in the comments — a future reader finding `align-items: start` cited in UXA-06's own artifacts, or 260901-tsa's "not edited" claim, must be able to see that this task knew and chose.

**Non-goals — verified, deliberately NOT touched.**
- **`.stat-tile__value`'s size.** Finding 4 is answered without it. 06.6.4 D-09 retired `--font-display-size` and moved this exact selector to the Emphasis role; the design skill (`.claude/skills/sketch-findings-skypane/SKILL.md`, `<design_direction>` Typography) records the surviving four-size scale as the current contract. If the developer still reads the tile value as under-weighted after the live pass, the next lever is re-opening D-09 as a design decision, not a quick-task size bump — say exactly that in the SUMMARY.
- **`.data-table`'s shared `min-width: max-content` floor.** Load-bearing for History's 7-column table and the unresolved-prefix registry, and cross-referenced from `.stat-tile`'s own `min-width: 0` comment. Only the one prose table opts out.
- **The Unresolved-prefixes table.** Its five columns hold short values (prefix, count, two timestamps, a callsign); its max-content width is bounded and the wrap absorbs it as designed. Not a prose table, no modifier, unchanged.
- **`.page-section` itself, and its use on Settings, History, and Health's own source-fault block.** Finding 4's demotion is carried by a modifier class only `health_page.py`'s two migrated cards emit. A bare `.page-section h2` rule would have silently resized Settings' Poll/LED groups and History's card, neither of which is nested under a section heading.
- **The `@media (min-width: 960px)` `.dashboard-shell { align-items: start }` declaration.** Different selector, different job — D-21's sticky sidebar explicitly requires it, and its own comment says so. Finding 1 is scoped to `.dashboard-grid`.
- **`companion/static/list-filter.js`, `freshness.js`, and every page module other than `health_page.py`.** `data_table()`'s new keyword defaults to `False`, which Task 2's verify gate proves byte-identical for every existing caller.
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
@companion/layout.py
@companion/static/style.css
@companion/static/battery-trend.js
@companion/test_status_pages.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Make same-row tiles match height, and restore the nested-heading tier</name>
  <files>companion/static/style.css, companion/pages/health_page.py, companion/test_status_pages.py</files>
  <read_first>
    - style.css's `.dashboard-grid` rule in full, INCLUDING the 06.6.3 (UXA-06) comment inside its body. Read what that comment claims the declaration is for before you remove it — this task reverses a stated decision, and the replacement comment has to say so honestly rather than reading as if the declaration was an accident.
    - style.css's `.stat-tile` rule and the long comment above it, especially the `min-width: 0` paragraph. Satisfy yourself that nothing in that rule (no `height`, no `align-self`, no absolutely-positioned child) is a second reason the tiles do not stretch — the grid declaration should be the only one, and the plan's claim that it is should be something you verified, not something you accepted.
    - The `@media (min-width: 960px)` block's `.dashboard-shell` rule and the `.dashboard-sidebar` comment immediately below it, which states that the sticky sidebar depends on that OTHER `align-items` declaration. Confirm for yourself that the two are separate selectors before editing either.
    - style.css's `.text-heading` rules (there are two: the serif/family one and the heading-rhythm margin one), `.page-title`, `.page-section`, and `.battery-trend-section`. Note that `.text-heading` supplies the serif family and `var(--weight-regular)`, and that a size is supplied by the earlier typography-role `.text-heading` rule — the demotion below overrides size and weight only and must leave the family alone.
    - `.claude/skills/sketch-findings-skypane/SKILL.md`, `<design_direction>` Typography and Controls sections in full. The four-size scale and the Display-role retirement are the constraint this task's finding-4 answer is built to respect; read them before writing the comment that cites them.
    - Every `page-section` emitter: `health_page.py::render()`'s two migrated cards, `health_page.py::_source_fault_block()`, `config_page.py` (its section), `history_page.py` (its section). Confirm for yourself that only the two in `render()` are nested inside a `.section-intro` heading — that nesting is the entire justification for demoting them and not the others.
    - `companion/test_status_pages.py::_server_data_grid_holds_three_tiles_migrated_cards_outside_grid()` in full. It locates `'<section class="page-section">'` by index and counts occurrences of that exact literal. Adding a modifier class breaks BOTH. Retargeting it is part of THIS task, not the harness task.
    - Grep the whole harness for the literal `page-section` and for `dashboard-grid` before editing, so you find every check that keys on either — do not rely on the one named above being the only one.
  </read_first>
  <action>
**A. `.dashboard-grid` — restore cross-axis stretch (finding 1).** Replace the cross-axis alignment declaration inside `.dashboard-grid`'s body with an explicit `align-items: stretch`. State it explicitly rather than deleting the line: `stretch` is the grid default, but an explicit declaration is greppable, is what the harness guard in Task 4 pins, and makes the reversal visible in a diff instead of invisible as a deletion.
<!-- planner-discipline-allow: align-items: start -->

Rewrite the comment inside that rule. It currently attributes the non-stretching behaviour to 06.6.3 (UXA-06) as a deliberate choice — that attribution is accurate and must be preserved, not overwritten as if it had been a bug. Say instead: UXA-06 chose intrinsic heights so Health's shorter tiles would not stretch beside a taller Corroboration tile; the developer has now measured the shipped result live (Pipeline 107.7px, Corroboration 261.8px, Resolution-rate 140.4px in one row) and asked for the opposite, so this is a reversal of UXA-06, not a fix of it. Record the direction the reversal runs: the shorter tiles grow to the tallest sibling; the Corroboration tile — naturally tallest because it carries three status rows plus a `<details>` disclosure — is never shrunk or clipped, which is what makes stretch the safe direction here. Record the blast radius as a fact you verified: `dashboard-grid` is emitted from exactly two places, both in `health_page.py::render()`, so this reaches Health and nothing else. And name the neighbour it must not be confused with: the `align-items` declaration in the `@media (min-width: 960px)` `.dashboard-shell` rule is a different selector that D-21's sticky sidebar depends on, and is untouched.

**B. `health_page.py` — mark the two nested cards (finding 4).** In `render()`, both migrated cards are emitted as `<section class="page-section">`. Give both a second, additive modifier class in the same class attribute, spelled exactly `page-section--nested` (the harness guards in Task 4 assert that literal), so each opening tag reads `<section class="page-section page-section--nested">`. The name states what it means structurally: a `page-section` nested inside a `.section-intro`-headed section, as opposed to a top-level one. Change nothing else about either line — same element, same heading markup, same content interpolation.

Do NOT add the modifier to `_source_fault_block()`'s `page-section banner banner--anomaly` section: that block renders above both sections, at the same structural level as the section headings themselves, so demoting its heading would understate a real fault. Add a short comment at the `render()` site recording that exclusion and its reason, so a later "make it consistent" edit has to argue with a written decision rather than an omission.

**C. `style.css` — demote the nested heading tier (finding 4).** Add one rule, placed immediately after `.page-section:hover, .page-section:focus-within` so the base card rule and its nested-heading variant read together. Its selector list is exactly `.page-section--nested > h2` and `.battery-trend-section > h2`, and it sets exactly two declarations: the Body size and the semibold weight — the Emphasis role. Use the child combinator on both, not a descendant selector: only each card's own title is being retiered, never a heading that might later appear deeper inside one.

Comment it with the finding and the reasoning a future reader needs, in this order.

First, the measured complaint: the tile's headline value (16px semibold) read as less prominent than an ordinary section heading below it (20px serif), which the developer called an inverted hierarchy.

Second, why the answer is not a bigger tile value: 06.6.4 (D-09) retired the Display role outright and moved `.stat-tile__value` and `.runway-card__number` to the Emphasis role, restoring this file's claimed four-size scale; the design skill records those four sizes as the current contract. Introducing a fifth size to win this one comparison would re-break exactly the claim that retirement was made to restore.

Third, what was actually wrong: Health renders two different structural levels at one identical visual tier — the D-10 section headings (`Screen`, `Server & data`) and the cards nested inside them (`Battery trend`, `Unresolved prefixes`, `Resolution statistics`), all 20px serif regular. A card title inside a section is subordinate to that section's heading and was rendering as its equal. Demoting the nested tier to the Emphasis role makes a card title and a tile value read as peers and leaves the section headings unambiguously on top, so the hierarchy now decreases with nesting depth instead of flattening.

Fourth, the two things this rule deliberately does not do: it sets no family, because `.text-heading` already supplies the serif treatment and the serif boundary is headings-only (the skill's own wording) — restating it here would create a second place that value lives; and it is scoped to an explicit modifier class rather than written as a bare `.page-section h2`, because that broader selector would have silently resized Settings' groups, History's card, and Health's own top-level source-fault block, none of which is nested under a section heading.

Note in the same comment that `.battery-trend-section`'s heading carries a 20px `<svg class="icon">` and a trailing `text-label` span, so at the demoted size the icon is now larger than the text beside it — the same proportion `.stat-tile__caption` (14px text, 20px icon) has already shipped and been validated with, which is why it needs no icon rule of its own.

**D. Retarget the checks B breaks, IN PLACE.** No `EXPECTED_CHECK_COUNT` movement in this task.

- `_server_data_grid_holds_three_tiles_migrated_cards_outside_grid()` keys on `'<section class="page-section">'` twice: once with `.index(...)` to find the first migrated card, once with `.count(...)` to assert there are exactly two. Both now match zero times. Retarget both onto the new modifier-bearing literal, and add an assertion that the source-fault block's own `page-section` is NOT modifier-bearing — that exclusion is the new invariant part B introduces and it belongs beside the one it mirrors. Derive every count by RUNNING the check against its real fixture; do not carry a number over from this plan's prose.
- Fix any other check the grep in `read_first` surfaced, in place, the same way.

After each of A through D, run `server/.venv/bin/python3 companion/test_status_pages.py` before moving to the next.
  </action>
  <verify>
    <automated>test "$(awk '/^\.dashboard-grid \{/,/^\}/' companion/static/style.css | grep -v '^ *\*' | grep -c 'align-items: stretch')" = 1 && server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
s = open('companion/static/style.css').read()
i = s.index('.dashboard-grid {')
grid = '\n'.join(l for l in s[i:s.index('}', i)].splitlines() if not l.lstrip().startswith('*'))
assert 'align-items: stretch' in grid, 'the grid must declare cross-axis stretch explicitly'
assert 'align-items: start' not in grid, 'a start-aligned .dashboard-grid returns the ragged tile heights'
assert s.count('align-items: start') == 1, 'the dashboard-shell sticky-sidebar declaration must be the only remaining one'
assert '.battery-trend-section > h2' in s, 'battery-trend heading missing from the demotion selector list'
i = s.index('.battery-trend-section > h2')
body = s[i:s.index('}', i)]
assert 'font-size: var(--font-body-size)' in body, 'demotion must set the Body size'
assert 'font-weight: var(--weight-semibold)' in body, 'demotion must set the semibold weight'
assert 'font-family' not in body, 'the serif family comes from .text-heading and must not be restated'
print('css ok')
" && server/.venv/bin/python3 -c "
import sys, tempfile, shutil; sys.path.insert(0, '.')
from companion.pages import health_page as h
d = tempfile.mkdtemp(); r = h.render({'state_dir': d}); shutil.rmtree(d, ignore_errors=True)
assert r.count('page-section--nested') == 2, 'exactly the two migrated cards carry the modifier, got %d' % r.count('page-section--nested')
assert r.count('class=\"stat-tile ') == 4, 'still four stat tiles'
assert r.count('<div class=\"dashboard-grid\">') == 2, 'still two dashboard grids'
assert r.count('<h2 id=\"') == 2, 'the two section headings are unchanged'
print('markup ok')
" && server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_config_page.py && server/.venv/bin/python3 companion/test_view_pages.py</automated>
  </verify>
  <done>
`.dashboard-grid` declares an explicit cross-axis stretch with the UXA-06 reversal, its direction, and its Health-only blast radius written into the rule's own comment; the only remaining start-aligned declaration in the file is `.dashboard-shell`'s. Health's two migrated cards carry a nested modifier and the source-fault block does not. One new rule demotes both nested card headings and the battery-trend heading to the Emphasis role, sets no family, and carries the D-09 / four-size-scale reasoning. Every check the modifier broke is retargeted in place and all three companion page harnesses pass at their unchanged `EXPECTED_CHECK_COUNT`s.
  </done>
</task>

<task type="auto">
  <name>Task 2: Let the Resolution-statistics description column wrap instead of overflowing</name>
  <files>companion/layout.py, companion/pages/health_page.py, companion/static/style.css</files>
  <read_first>
    - `layout.data_table()` in full, including the whole `raw_columns` paragraph in its docstring — that parameter is this file's own precedent for adding one optional, default-inert keyword to this builder, and the new one should read as its sibling.
    - Every `data_table(` call site. Grep for it across `companion/` before assuming: there are exactly two production callers (both in `health_page.py`) plus harness calls; History and the unresolved-prefix registry hand-roll their tables instead, for reasons their own docstrings give. Confirm this yourself — the "default-inert, therefore byte-identical" claim below rests on it.
    - style.css's `.data-table-wrap`, `.data-table`, `.data-table th`, `.data-table-wrap th` and `.data-table td` rules and every comment above them. `.data-table` declares BOTH `width: 100%` and `min-width: max-content`; the second is the one that matters here, and `.stat-tile`'s own `min-width: 0` comment cross-references it as load-bearing for a different failure mode. Read that cross-reference before touching anything.
    - `health_page.py::_stats_table_html()` and `_SOURCE_ROWS` — look at the actual sentences in the third element of each tuple, which is what lands in the Description column and what makes this table's max-content width unbounded in a way the registry table's never is.
    - `health_page.py::_registry_table_html()` — the hand-rolled table this task deliberately does NOT change, so you can see for yourself that its five columns hold short values only.
    - Grep the harness for `'<table class="data-table">'` and for `data-table` generally: at least one check asserts that exact opening-tag literal, and you need to know whether it is reading the battery readings table (unaffected) or the stats table (affected) before you finish.
  </read_first>
  <action>
**A. `layout.py` — one optional keyword.** Add a keyword-only-in-spirit `prose=False` parameter to `data_table()`, after `raw_columns`. When truthy, the emitted `<table>` carries an additional modifier class alongside `data-table`; when falsy (the default), the opening tag is byte-identical to what it emits today. Change nothing else in the function — not the cell escaping, not `mono_columns`, not `raw_columns`, not the wrapper div.

Document it in the docstring as its own paragraph, in the same voice as the `raw_columns` paragraph above it. Say what it is for in terms of the real defect: `.data-table` carries `min-width: max-content` so that tables of short values are never cropped, and a cell's max-content width is its text with no wrapping at all — which is correct for callsigns, hex codes, prefixes and timestamps, and wrong for a column holding full sentences, because the table then cannot fit any container narrower than the whole unwrapped sentence and the wrapper's horizontal scroll becomes a permanent state rather than a safety net. Say plainly that this keyword does not change any cell's content or escaping: it only adds a class the stylesheet uses to release that one table from the shared no-crop floor. Name the measurement that prompted it (the Resolution-statistics table measured 1172px of content inside an 831px container) so a reader can tell this was observed, not theorised.

**B. `health_page.py` — opt the one prose table in.** Pass the new keyword at `_stats_table_html()`'s `data_table()` call. Leave the battery readings table's call (with its `mono_columns` / `raw_columns` arguments) exactly as it is — its Timestamp and mV columns are short values and it must keep the no-crop floor.

Extend `_stats_table_html()`'s docstring with one short paragraph: this is the only table in the app whose Description column carries real prose (the `_SOURCE_ROWS` glosses, up to full sentences), which is why it is the only one that opts out; the unresolved-prefix registry directly above it on the same page is deliberately NOT opted out, because its five columns hold short values whose combined max-content width is bounded and which the wrapper absorbs exactly as designed.

**C. `style.css` — the modifier rule.** Add `.data-table--prose` immediately after the `.data-table` rule, setting its minimum width to zero so the shared floor no longer applies to it.

Comment it with three things.

First, the mechanism, in full: `.data-table` and `.data-table--prose` are both single-class selectors landing on the same element, so their specificity is equal and SOURCE ORDER is the only thing deciding which minimum width wins. This rule must therefore stay after `.data-table` in the file. Say that moving it above would silently restore the overflow with nothing else in the file to notice, and note that Task 4 pins the ordering with a check rather than leaving it to this comment.

Second, why no fixed pixel floor is added to the Description column even though the sketch this page came from used one. A minimum wider than the narrowest container simply re-creates the same overflow one breakpoint down, which is the exact defect being fixed; and it is not needed, because the other two columns (a short source label and a count) have small max-content widths, so the table's own auto layout already gives the description column the large majority of the available width and wraps it there. `.data-table-wrap`'s `overflow-x: auto` remains the backstop for any residue at extreme widths — used as the safety net it was written to be rather than as the normal state.

Third, the boundary: this releases exactly one table. The floor stays in force for History's wide table and for the unresolved-prefix registry, and `.stat-tile`'s own `min-width: 0` comment still describes a real, unrelated failure mode that depends on it.

**D. Fix in place whatever the harness grep in `read_first` surfaced.** If a check asserts the bare `'<table class="data-table">'` literal against the stats table, retarget it onto the modifier-bearing form; if it is reading the battery readings table, leave it alone and say so in your commit message. No `EXPECTED_CHECK_COUNT` movement in this task.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
s = open('companion/static/style.css').read()
base = s.index('.data-table {')
prose = s.index('.data-table--prose {')
assert base < prose, 'equal specificity means source order decides: .data-table--prose must follow .data-table'
body = s[prose:s.index('}', prose)]
assert 'min-width: 0' in body, 'the modifier must neutralise the max-content floor'
assert 'min-width: max-content' in s[base:s.index('}', base)], 'the shared no-crop floor must stay on .data-table'
print('css ok')
" && server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
from companion import layout
plain = layout.data_table(['A', 'B'], [['1', '2']])
assert '<table class=\"data-table\">' in plain, 'default-off callers must be byte-identical'
assert 'data-table--prose' not in plain, 'no modifier without the keyword'
prose = layout.data_table(['A', 'B'], [['1', '2']], prose=True)
assert 'data-table--prose' in prose, 'keyword must add the modifier'
assert prose.replace(' data-table--prose', '') == plain, 'the keyword must change the class list and nothing else'
print('builder ok')
" && server/.venv/bin/python3 -c "
import sys, tempfile, shutil; sys.path.insert(0, '.')
from datetime import datetime, timedelta, timezone
from server import history_db as hd
from companion.pages import health_page as h
d = tempfile.mkdtemp(); n = datetime.now(timezone.utc)
with hd.open_db(d) as conn:
    for off, mv in ((2, 4200), (1, 4190)):
        hd.record_device_health(conn, (n - timedelta(minutes=off)).isoformat(timespec='seconds'), battery_mv=mv)
r = h.render({'state_dir': d}); shutil.rmtree(d, ignore_errors=True)
assert r.count('data-table--prose') == 1, 'exactly one table opts out, got %d' % r.count('data-table--prose')
stats_at = r.index('Resolution statistics')
assert r.index('data-table--prose') > stats_at, 'the opted-out table must be the Resolution-statistics one'
print('markup ok')
" && server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_companion_app.py && server/.venv/bin/python3 companion/test_view_pages.py</automated>
  </verify>
  <done>
`data_table()` carries one optional, default-inert `prose` keyword whose only effect is the table's class list, documented against the real 1172-in-831 measurement and proven byte-identical for every existing caller. Only the Resolution-statistics table passes it; the battery readings table and the hand-rolled registry table are untouched. `.data-table--prose` sits after `.data-table` in the stylesheet with the source-order dependency, the no-fixed-floor reasoning and the release boundary all written down. Every affected harness check is retargeted in place and `companion/test_status_pages.py` passes at its still-unchanged `EXPECTED_CHECK_COUNT`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Humanise the battery readout end-to-end, server and script</name>
  <files>companion/pages/health_page.py, companion/static/battery-trend.js, companion/static/style.css, companion/test_status_pages.py</files>
  <read_first>
    - `companion/static/battery-trend.js` in full, especially its header comment (the "no network call, no timer, no persistent state ... its entire job is reading attributes already present in the DOM and writing one line of text" charter, and the `textContent`-is-the-only-sink / ASVS V5 paragraph) and `reveal()`'s own body. `reveal()` composes the readout text itself. That single line is why this finding cannot be fixed server-side alone, and the charter is why the humanised string must be READ from an attribute rather than formatted in JavaScript.
    - The comment at the top of the file about the script shipping one wave ahead of the markup that references it, and the early-return that exists because of it. That is the precedent for the fallback branch this task adds.
    - `layout.concise_timestamp_html()` in full — it is the humanised pattern every other timestamp on this page already uses, and its unparseable-`ts` branch is the graceful-degradation shape the new plain-text helper must copy. Note that it returns MARKUP, which is precisely why it cannot be reused directly for a value a `textContent` write will overwrite.
    - `layout.relative_age_text()`, `layout.parse_iso()`, `layout.age_seconds()` and `layout.absolute_and_relative()` — the last of these is the existing plain-text timestamp helper; read its "plain, unescaped text, every caller must keep escaping it" contract, which the new helper inherits.
    - `health_page.py::battery_sparkline_svg()` in full, especially the per-point `label` construction and the comment above it claiming the label is byte-identical in shape to what `battery-trend.js` composes. That claim is currently true and this task must keep it true by changing both sides together — update the comment to describe the new arrangement rather than leaving a claim that has quietly stopped holding.
    - `health_page.py::_latest_numeric_battery_label()`, `_battery_readout_block()`, `_battery_section()`'s `chart_block` assembly, and style.css's `.battery-readout`, `.mono`, `.stat-tile__value` and `.stat-tile__value .mono` rules.
    - `companion/test_contrast_check.py`'s `live_pairs` tuple. The new muted detail text uses this file's existing 70% `color-mix` strength on a card surface; check whether that foreground/background pair is already pinned there. If it is, change nothing in that file and say so; if it is not, adding it is part of this task.
    - The checks this task WILL break, all in `companion/test_status_pages.py`: `_battery_readout_seeded_with_latest_reading_not_placeholder()` (asserts the old raw-ISO label), `_battery_readout_precedes_chart_class_list_and_live_region()` (asserts an exact two-class list on the readout), and the CSS DOM-contract guard that reads `.battery-readout`'s rule body. Grep as well for `_latest_numeric_battery_label` and for the hostile-timestamp check that asserts an escaped value reaches `data-ts` and `<title>` — you need to know whether renaming the helper or changing the tooltip format touches either. Retargeting all of them is part of THIS task.
  </read_first>
  <action>
**A. `health_page.py` — one plain-text formatting helper, used everywhere.** Add a module-level helper that takes a millivolt integer, a timestamp and a `now`, and returns a two-element plain-text tuple: the value part (the millivolt figure with its unit) and the "when" part in the same shape `concise_timestamp_html()` renders visibly — a short clock time plus the existing `relative_age_text()` suffix. Return plain, unescaped text and say so in the docstring, inheriting `absolute_and_relative()`'s stated contract: every caller escapes at the point of interpolation.

Copy `concise_timestamp_html()`'s degradation shape exactly: when the timestamp is missing, or fails to parse, or the age cannot be computed, the "when" part falls back to the raw timestamp string rather than raising. Say in the docstring that this fallback is what keeps the existing hostile-timestamp harness check meaningful — an unparseable attacker-supplied value still reaches the tooltip, still through `escape_html()`, exactly as before.

Explain in the docstring why this returns a plain-text TUPLE and not markup, since that is the non-obvious part: the readout's content is rewritten by `battery-trend.js` through `textContent`, so anything the server puts there as markup is destroyed on the first hover; the two parts exist separately so the script can write each into its own span and preserve the value/detail split rather than flattening it back to one string.

**B. `health_page.py` — share it across all four consumers.** Give `battery_sparkline_svg()` an optional `now` parameter defaulting to the same `history_db.utc_now_iso()` call the rest of this module uses, so every existing call site (including the harness's) keeps working unchanged, and thread `_battery_section()`'s already-computed `now` through at its call site rather than computing a second one.

Then, inside the per-point loop, build the pair with the new helper and use it for all three of the point's human-facing strings: the `<title>` tooltip, the `aria-label`, and a NEW attribute spelled exactly `data-when` (the harness and the script both key on that literal) carrying the "when" part alone. Escape each at interpolation, exactly as the current code escapes the timestamp. Leave `data-mv` and `data-ts` exactly as they are — `data-ts` remains the machine-precise value and is what the tooltip attribute is set from.

Replace `_latest_numeric_battery_label()` with a function that returns the latest numeric row's `(millivolts, timestamp)` rather than a pre-formatted label — the same newest-first scan and the same int-not-bool filter, just stopping before the formatting so the caller can build both parts and still hold the raw timestamp for the tooltip. Grep the harness for the old name first and retarget any reference in place.

Rewrite `_battery_readout_block()` to take the reading and `now` and emit the element as: the same `id`, the same `role="status"`, `class="battery-readout"` (the `mono` class moves off the paragraph), containing `<span class="battery-readout__value mono">` holding the value part and `<span class="battery-readout__detail" title="{raw ISO}">` holding a separator plus the "when" part. Both class names are literals the stylesheet, the script and Task 4's checks all key on — spell them exactly. Escape every interpolated part.

Update that function's docstring with what changed and what did not. What changed: the readout used to print the raw ISO string inline, which is the one timestamp on this page that did not follow the house humanised pattern, and read as heavy — the developer's words were too bold, too big, not sober. It now reads as a scannable figure plus a muted trailing detail, which is the original validated sketch's own `.battery-readout` treatment (the voltage emphasised, the trailing detail muted), and the machine-precise ISO moved to a `title` tooltip exactly as `concise_timestamp_html()` does everywhere else. What did not change: the element `id` and `role="status"`, so `getElementById` and the Left/Right/Home/End live-region announcements are untouched. Note that the humanised string is strictly SHORTER than the raw-ISO one it replaces, so the reserved-height no-layout-jump guarantee is not weakened but strengthened — the old format was long enough to wrap at narrow widths and the new one is not.

Update `battery_sparkline_svg()`'s own comment above the label construction so its "byte-identical in shape to what the script composes" claim describes the new arrangement — the server now builds the string and the script reads it, which makes them identical by construction rather than by two matching format literals.

**C. `battery-trend.js` — read the humanised parts, keep the old path as a fallback.** This file IS edited. Quick task 260901-tsa listed it as explicitly not edited; that was correct for a pure reposition and is not correct here, because this file builds the readout's format itself and a server-only change is undone by the user's first hover. Record that reversal in a comment.

Look up the two spans once, beside the existing readout lookup, using `querySelector` on the readout element. In `reveal()`, read the new per-point attribute; when it and both spans are present, write the value into the value span and the separator-prefixed detail into the detail span, and set the detail span's `title` to the machine-precise timestamp. When any of the three is absent, fall through to the existing composition written to the readout's own `textContent`, unchanged.

Comment the fallback with the reason this file's own header already establishes: this script is a single cached static asset served to every page and can be one wave out of step with the markup that references it, which is the same reason the existing early-return exists. A missing attribute must degrade to the old readable line, never to an empty readout.

Comment the security posture explicitly so the next reader does not have to re-derive it: `textContent` is still the only content sink, and the one new attribute write is `title`, which is not an HTML sink — so this file still needs no escaping function and 06.5-RESEARCH.md's ASVS V5 reasoning is unchanged. Keep the ES5-safe subset: no `let`, no `const`, no arrow functions, no template literals.

**D. `style.css` — the two-tone treatment.** Leave `.battery-readout`'s existing declarations alone: the Body size, the semibold weight, the reserved `min-height` and the bottom margin all still apply, and they now reach only the value span because the detail span overrides them for itself.

Extend the existing `.stat-tile__value .mono` rule into a two-selector list so it also covers a `.mono` descendant of `.battery-readout`. Do not write a second rule: this is one role — an Emphasis-weight container holding a `.mono` span whose own rule would otherwise pin it to regular — and it should have one implementation. Extend that rule's existing comment to name the second container and say why it joined rather than getting a rule of its own. Keep `.stat-tile__value .mono` as the first selector in the list so the existing harness guard that locates the rule by that literal still finds it.

Add `.battery-readout__detail` immediately after: the Label size, the regular weight, and this file's existing 70% `color-mix` muted strength — the same value `.section-caption`, `.data-table th` and `.filter-bar__count` already use. Comment it against the developer's actual complaint (too bold, too big, not sober): the readout keeps exactly one emphasised element, the figure, and everything trailing it recedes, which is the validated sketch's own arrangement. Say explicitly that the muted strength is the file's existing one and not a fourth value invented here, and record the result of the `live_pairs` check from `read_first` — either that the muted-on-card-surface pair is already pinned in `test_contrast_check.py`, or that you added it.

**E. Retarget the checks this task breaks, IN PLACE.** No `EXPECTED_CHECK_COUNT` movement in this task.
- The seeded-readout check asserts the old raw-ISO label. Rebuild its expectation from the new helper's own return value rather than re-typing a format string into the harness — the harness must not become a second place this format lives. Update its `check(...)` description to say what it now proves.
- The readout position/class-list/live-region check asserts an exact two-class list. Update it to the new class list, and extend it in place with an assertion that the value and detail spans are both present and that `role="status"` and the id still are. Its position and script-ordering assertions stay as they are.
- The CSS DOM-contract guard reads `.battery-readout`'s rule body for the semibold weight — still true, so leave that entry alone; verify by running, not by reading.
- Confirm the hostile-timestamp check still passes, and if the tooltip format change moved what it matches, retarget it onto the same property it was always testing: that an attacker-supplied timestamp reaches the attribute and the tooltip escaped, never raw.

After each of A through E, run `server/.venv/bin/python3 companion/test_status_pages.py` before moving to the next.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -c "
import sys, tempfile, shutil; sys.path.insert(0, '.')
from datetime import datetime, timedelta, timezone
from server import history_db as hd
from companion.pages import health_page as h
d = tempfile.mkdtemp(); n = datetime.now(timezone.utc)
for off, mv in ((6, 4210), (3, 4200), (1, 4190)):
    with hd.open_db(d) as conn:
        hd.record_device_health(conn, (n - timedelta(minutes=off)).isoformat(timespec='seconds'), battery_mv=mv)
import re
r = h.render({'state_dir': d}); shutil.rmtree(d, ignore_errors=True)
start = r.index('<p id=\"%s\"' % h.BATTERY_READOUT_ID)
readout = r[start:r.index('</p>', start)]
assert 'role=\"status\"' in readout, 'live region must survive'
assert 'battery-readout__value' in readout and 'battery-readout__detail' in readout, 'two-part readout'
assert 'UTC (' in readout, 'the readout must carry the humanised clock format'
visible = re.sub(r'<[^>]*>', '', readout)
assert not re.search(r'\d{4}-\d{2}-\d{2}T', visible), 'no raw ISO in the readout visible text: %r' % visible
assert re.search(r'\d{4}-\d{2}-\d{2}T', readout), 'the machine-precise ISO must survive in the tooltip attribute'
assert r.count('data-when=') == 3, 'one data-when per hit target, got %d' % r.count('data-when=')
assert r.count('data-mv=') == 3 and r.count('data-ts=') == 3, 'machine attributes unchanged'
assert r.index(h.BATTERY_READOUT_ID) < r.index('<svg'), 'readout still precedes the chart'
assert r.index('<svg') < r.index('<script'), 'script still follows the chart'
print('markup ok')
" && server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
js = open('companion/static/battery-trend.js').read()
for token in ('data-when', 'battery-readout__value', 'battery-readout__detail', 'getElementById'):
    assert token in js, 'battery-trend.js must reference %s' % token
assert 'readout.textContent' in js, 'the pre-data-when composition must survive as the fallback branch'
assert js.count('.textContent') >= 3, 'value span, detail span and the fallback all write textContent'
for sink in ('innerHTML', 'insertAdjacentHTML', 'outerHTML', 'document.write'):
    assert sink not in js, 'textContent must remain the only content sink, found %s' % sink
print('js ok')
" && server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
s = open('companion/static/style.css').read()
i = s.index('.stat-tile__value .mono')
rule = s[i:s.index('}', i)]
assert 'font-weight: inherit' in rule, 'the scoped Emphasis reach-through must survive'
assert '.battery-readout .mono' in rule, 'the readout container must join the same rule, not get a second one'
j = s.index('.battery-readout__detail {')
detail = s[j:s.index('}', j)]
assert 'font-size: var(--font-label-size)' in detail and 'font-weight: var(--weight-regular)' in detail, 'detail must recede'
assert 'color-mix(in srgb, var(--color-text) 70%, transparent)' in detail, 'reuse the file existing muted strength'
print('css ok')
" && server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_contrast_check.py</automated>
  </verify>
  <done>
One plain-text helper builds the `(value, when)` pair and feeds the seeded readout, each point's tooltip, each point's `aria-label` and the new `data-when` attribute, with `concise_timestamp_html()`'s own unparseable-input fallback copied so the hostile-timestamp guarantee holds. `battery_sparkline_svg()` takes an optional `now` and every existing caller still works. The readout renders as an emphasised figure plus a muted, humanised trailing detail with the ISO in a tooltip, keeping its id and `role="status"`. `battery-trend.js` reads the attribute, writes both spans, sets the tooltip, keeps the old composition as an explicit one-wave-skew fallback, keeps `textContent` as its only content sink and stays ES5-safe. The `.mono` reach-through is one rule covering both containers. Every broken check is retargeted in place, `companion/test_status_pages.py` passes at its unchanged `EXPECTED_CHECK_COUNT`, and the contrast harness passes.
  </done>
</task>

<task type="auto">
  <name>Task 4: Investigate the Safari disclosure report, pin the four fixes, and verify against a real running service</name>
  <files>companion/test_status_pages.py</files>
  <read_first>
    - `companion/test_status_pages.py`'s `EXPECTED_CHECK_COUNT` and the whole provenance comment block above it — read the REAL on-disk value at execution time; this plan deliberately names no number.
    - The `check(name, fn)` helper at the top of `main()` for the return-tuple contract, and `_mkstate` / `_ctx` / `_iso` / `_now` / `_seed_device_health` / `_seed_meta` / `_seed_unresolved_prefixes` / `_seed_runway_events`.
    - The existing cross-file CSS DOM-contract guard 260901-tsa added (the one asserting declarations inside located rule bodies and the `.mono`-before-`.battery-readout` source-order fact) — the new stylesheet guards below extend that same idiom and belong beside it.
    - Section 3's `Harness` block and its `_both_tabs_ok_end_to_end()` check — this task extends that existing check in place rather than adding a second live one.
    - For the finding-5 investigation only: style.css's `summary`, `summary::marker`, `summary::-webkit-details-marker`, `.readings-disclosure`, `.data-table-wrap`, `.data-table th` and `.data-table-wrap th` rules, together with every comment above them; and `health_page.py::_battery_section()`'s `disclosure_html` construction plus `_corroboration_details_html()`. Read all of it fresh before forming any hypothesis.
  </read_first>
  <action>
**Part 1 — the finding-5 investigation. Produce a written verdict, not a speculative fix.**

The developer reported, in real Safari, that the readings-history disclosure's table header appears half-cut-off when the disclosure is opened. The orchestrating session already measured the disclosure's `.data-table-wrap` live in a Chromium-based tool and found no vertical clipping at all (`clientHeight` equal to `scrollHeight`), and found no `max-height`, `overflow` or sticky mechanism on `.readings-disclosure` itself.

Read the rule set named in `read_first` and decide for yourself whether a source-only root cause is reachable. Two candidates are already identified; confirm or reject each against the real file, and look for a third rather than stopping at these.

- The header cells declare horizontal and bottom padding with no top padding at all, while `.data-table-wrap th` makes them sticky at the scroll container's top edge. A stuck header therefore has zero space above its glyphs, so whether the ascenders visibly clip depends on font ascent metrics inside the line box — which genuinely differ between WebKit and Blink, and would make this exactly the kind of defect that reproduces in Safari and not in the tool used to check it.
- `.data-table-wrap th` paints its sticky background from the page-canvas token while these tables render inside a card surface. This file's own comment already pre-registers that as never live-validated and names the card-surface token as the equally-valid alternative on a closing checklist.

Ship NO CSS change for either. The first would re-space every table header in the app, including three pages nobody reported a problem on. The second would fix the in-card tables by breaking the one table the same comment says is the only one long enough for the sticky state to reliably engage. Neither is a change to make blind.

Write the verdict into the SUMMARY: whether a root cause was reached, which candidates were confirmed or rejected and on what evidence, the exact reproduction the developer's next Safari pass should run (open the disclosure, scroll the table's own wrapper vertically and horizontally, and report whether the clipping tracks the scroll or is present at rest), and the one-declaration change each candidate would need if confirmed. If your fresh read DOES reach a conclusive cause with no such trade-off, fix it and add a sixth check — but do not manufacture confidence to avoid leaving an item open.

**Part 2 — add exactly five checks, extend one in place, and bump the count.**

**Check 1 — same-row tiles stretch.** A stylesheet guard beside the existing CSS DOM-contract check. Locate `.dashboard-grid`'s rule body, assert it declares the stretch alignment and does not declare the start alignment, and assert that the file's only remaining start-aligned declaration is the one inside the desktop `.dashboard-shell` rule. Fail with a message saying in words that a start-aligned `.dashboard-grid` returns the ragged-height tiles the developer measured, and that the `.dashboard-shell` declaration is a different selector the sticky sidebar needs.

**Check 2 — the nested heading tier.** Render Health and assert: exactly two sections carry the nested modifier; both are the migrated cards, located by slicing from each card's own heading constant rather than by first-occurrence index; the source-fault block's `page-section` does not carry it; and both `.section-intro` headings are unmodified. Then, in the same check, assert the stylesheet's demotion rule sets the Body size and the semibold weight and sets no font family. Reference every heading through the module's own constants — never re-type a heading string.

**Check 3 — the prose table opts out alone.** Assert on a seeded render that exactly one table carries the prose modifier, that it is the Resolution-statistics one (located from that section's own heading constant), and that neither the battery readings table nor the unresolved-prefix registry table carries it. Then assert the two stylesheet facts the fix rests on: `.data-table` still declares the max-content floor, and `.data-table--prose` declares a zero minimum AND appears later in the file. Fail with a message saying explicitly that equal specificity makes source order the deciding factor here.

**Check 4 — the humanised readout, end to end.** On a multi-reading fixture, slice to the battery-trend section's own boundaries and assert within that slice: the readout carries its id, `role="status"`, a value span and a detail span; the visible detail text is the humanised clock-plus-relative form and not a raw ISO string; the machine-precise timestamp is present as a tooltip attribute. Then assert the cross-file half: every chart hit target carries the new attribute, and `battery-trend.js`'s shipped source references that attribute name, both span class names, and still looks the readout up by its id literal. Fail with a message naming which half failed — a server-side format change that the script does not read is the specific regression this check exists to catch.

**Check 5 — the readout's typographic split.** A stylesheet guard: the `.mono` reach-through rule covers both the tile-value container and the readout container in one rule, and the detail rule carries the Label size, the regular weight and this file's existing muted strength. Fail with a message naming which selector or declaration is missing, matching the neighbouring guards' error style.

**In-place extension — the live-HTTP check.** Extend Section 3's existing `_both_tabs_ok_end_to_end()` rather than adding a new one (no count change): after its existing per-route status and heading assertions, for the `/health` response body only, assert that the nested modifier appears twice, the prose modifier appears once, the readout's two spans are present, and no raw ISO string appears in the readout's own slice. This is the automated half of "verified against a real running service" — a real subprocess, a real login, a real seeded database, a real HTTP response. Update the `check(...)` description to say so.

**Falsifiability pass.** Before finalizing, mutate all five new checks at once so each asserts on a name that does not exist in the source it reads, run the harness, and confirm the output reports exactly those five as FAIL and nothing else. Then restore them. A check that cannot be observed failing is not a check.

**Count bump.** Read the current on-disk `EXPECTED_CHECK_COUNT` and set it to that value plus exactly 5. Do not carry a number over from this plan text. Extend the provenance comment block above it with one new entry in that block's own established format: name this quick task, list the five checks added, and record that Tasks 1 through 3's retargets and this task's live-HTTP extension were all in place with no count change.

**Full suite.** Run `scripts/run-all-tests.sh`. The only harness in its FAILED list must be `server/test_poll_loop.py` — the known, pre-existing, unrelated digest mismatch. If any other harness fails, or if the coverage gate reports a new shortfall, stop and fix it before finishing this task; do not record a green result over a new failure.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py && test "$(server/.venv/bin/python3 companion/test_status_pages.py | tail -1 | sed 's#.*: \([0-9]*\)/\([0-9]*\).*#\1-\2#')" = "$(grep '^EXPECTED_CHECK_COUNT = ' companion/test_status_pages.py | sed 's/.*= //' | awk '{print $1"-"$1}')" && scripts/run-all-tests.sh > /tmp/skypane-uzi-run-all-tests.log 2>&1; test "$(sed -n '/FAILED harnesses/,$p' /tmp/skypane-uzi-run-all-tests.log | grep -c '^    - ')" = 1 && sed -n '/FAILED harnesses/,$p' /tmp/skypane-uzi-run-all-tests.log | grep -q 'server/test_poll_loop.py'</automated>
    <human-check>
REQUIRED, not optional — this project's own memory records that computed-style and structural checks alone have already missed a real rendered bug once (`feedback_real_device_ui_verification`), and the immediately-prior quick task's executor had no browser tooling and had to hand this pass back to the orchestrating session. Assume the same here: do NOT block plan completion on this.

The live-HTTP half is already automated and is NOT optional: it is the in-place extension to Section 3's `_both_tabs_ok_end_to_end()`, which starts a real `companion/app.py` subprocess against a real seeded state directory, signs in, and fetches `/health` over HTTP. Read that response body's assertions when they pass and record in the SUMMARY what the served HTML actually contained. Then hand the remaining pixel-level confirmation to the orchestrating session by naming it explicitly.

The pixel-level items that a raw-HTML check genuinely cannot settle, and which the SUMMARY must list as outstanding:
1. The three Server &amp; data tiles now measure the same height in a real browser, with the Corroboration tile still the one setting that height and neither of the shorter two clipped or oddly hollow-looking at its new height — the last part is a judgement call, not a measurement.
2. The Resolution-statistics table no longer scrolls horizontally: its wrapper's `scrollWidth` equals its `clientWidth` at desktop width, and the Description column wraps to multiple lines instead of running off. Re-measure at roughly 375px too, where the column is tightest.
3. The battery readout reads as one emphasised figure followed by muted, humanised detail — and hovering, tapping and arrowing (Left/Right/Home/End) through the chart still updates it in place, in that same two-tone form, without reverting to a raw timestamp and without the chart shifting. The arrow-key path is the one that most easily regresses silently.
4. The two card headings below the grid (&quot;Unresolved prefixes&quot;, &quot;Resolution statistics&quot;) and the &quot;Battery trend&quot; heading now read as subordinate to &quot;Screen&quot;/&quot;Server &amp; data&quot; above them, and the tile value no longer reads as the weakest thing on screen. If the developer still reads the tile value as under-weighted after this, say so — the next lever is re-opening 06.6.4 D-09, not a quick-task size bump.
5. Finding 5 specifically, in real Safari: open the readings disclosure and report whether the header clipping reproduces, and whether it is present at rest or only once the table's own wrapper is scrolled.

Record what was actually observed rather than restating this list as if performed, and stop the service and delete the tmpdir afterwards.
    </human-check>
  </verify>
  <done>
`companion/test_status_pages.py` passes with every check green, its printed total equals the new `EXPECTED_CHECK_COUNT`, and that value is the real on-disk baseline plus exactly 5. The provenance comment records this task's five additions and the in-place retargets and live-HTTP extension as no-count-change edits. Each new check was observed failing under mutation before being restored. `scripts/run-all-tests.sh` lists exactly one failing harness, `server/test_poll_loop.py`. A real `companion/app.py` process served a real `GET /health` whose body carried the new markup, and the SUMMARY records both what that response contained and the precise list of pixel-level items still outstanding for the orchestrating session's browser pass — including finding 5, explicitly left open with its two named candidates and their trade-offs.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser -> `GET /health` | Server-rendered HTML reaching an authenticated operator's browser. Every dynamic value on this page passes through `escape_html()` or one of `companion/layout.py`'s escaping component builders. |
| `history_db` state files -> `render()` | Device telemetry (including the `battery_mv` and `ts` values this task reformats) and the hand-editable unresolved-prefix registry. Every read still goes through `_safe_query()` or `unresolved_rows()`'s own defensive parse; no read path is changed. |
| rendered DOM attributes -> `battery-trend.js` | A new `data-when` attribute crosses into client-side code. Its value is server-built and escaped at interpolation; the script reads it and writes it through `textContent`. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-uzi-01 | Tampering (XSS) | The new `data-when` attribute and the humanised `(value, when)` helper | low | mitigate | The helper returns plain, unescaped text under `absolute_and_relative()`'s stated contract, and every one of its four consumers escapes at the point of interpolation exactly as the raw-timestamp code it replaces did. Its unparseable-input branch returns the raw timestamp, which is then escaped on the same path — so an attacker-supplied timestamp reaches the attribute and the tooltip escaped, never raw, and Task 3 keeps the existing hostile-timestamp harness check pointed at that property. |
| T-uzi-02 | Tampering (XSS) | `battery-trend.js`'s new attribute read and span writes | low | mitigate | `textContent` remains the only content sink; the one added attribute write is `title`, which is not an HTML sink. No `innerHTML`/`insertAdjacentHTML` is introduced and Task 3's verify gate asserts their absence, so 06.5-RESEARCH.md's ASVS V5 reasoning ("this file needs no escaping function at all") holds unweakened. |
| T-uzi-03 | Denial of Service | Accessibility regression from the readout's two-span split | medium | mitigate | The element keeps its `id` and its `role="status"` live region, and mutations to a live region's descendants are announced the same as mutations to its own text node, so the Left/Right/Home/End reveal announcements survive. Task 3's Check 4 pins id, role, both spans, the tooltip and the script-side reads together, and the human-check names the arrow-key path as the one that regresses silently. |
| T-uzi-04 | Denial of Service | Accessibility regression from demoting the nested heading tier | medium | mitigate | Size and weight change; the elements stay real `<h2>` elements with unchanged text, so the document outline, the heading-navigation order and every id anchor are untouched — including `#server-data`, the cross-page link `history_page.py` depends on. The demotion moves those headings to an existing role already in use elsewhere on the same page, so no new contrast pair is introduced. |
| T-uzi-05 | Information Disclosure | The muted `.battery-readout__detail` text | low | mitigate | Uses this file's single existing 70% `color-mix` muted strength on a card surface rather than a new value. Task 3's `read_first` requires checking `test_contrast_check.py`'s `live_pairs` for that exact pair and adding it if absent, so an under-contrast trailing detail fails a harness rather than a reader's eyes. |
| T-uzi-06 | Tampering | `layout.data_table()`'s new keyword reaching callers this task does not intend to change | low | mitigate | The parameter defaults to falsy and its only effect is the `<table>` class list. Task 2's verify gate asserts that the default output is byte-identical to today's and that the enabled output differs by exactly the added class, and runs the three companion page harnesses plus `test_companion_app.py`, which owns this builder's own escaping checks. |
| T-uzi-SC | Tampering | npm/pip/cargo installs | n/a | accept | No package-manager install of any kind. This task edits one stylesheet, one JavaScript file, two Python modules and one harness, all stdlib-only, with no dependency change. |
</threat_model>

<verification>
1. `server/.venv/bin/python3 companion/test_status_pages.py` — all checks pass; the printed total equals the new `EXPECTED_CHECK_COUNT`, which is the real on-disk baseline plus exactly 5.
2. `companion/test_config_page.py`, `companion/test_view_pages.py`, `companion/test_companion_app.py` and `companion/test_contrast_check.py` — all pass at their own unchanged `EXPECTED_CHECK_COUNT`s, proving the `data_table()` keyword, the heading demotion and the muted detail colour reached no other page.
3. `scripts/run-all-tests.sh` — exactly one harness in the FAILED list, `server/test_poll_loop.py` (known pre-existing digest mismatch). Coverage gate reports no new shortfall.
4. `git diff --stat` touches only `companion/layout.py`, `companion/pages/health_page.py`, `companion/static/battery-trend.js`, `companion/static/style.css`, `companion/test_status_pages.py` — plus `companion/test_contrast_check.py` if and only if Task 3's `live_pairs` check found the muted pair unpinned. No other page module appears.
5. `git diff companion/static/style.css` shows exactly five rule changes: `.dashboard-grid`'s alignment reversed with its comment rewritten; `.data-table--prose` new, after `.data-table`; the nested-heading demotion new, after `.page-section:hover`; `.stat-tile__value .mono` extended to a two-selector list; `.battery-readout__detail` new. No other rule's declarations changed, and no new custom property, size, muted strength or `:has()` selector appears anywhere.
6. `git diff companion/static/battery-trend.js` shows only the two span lookups, `reveal()`'s new branch and its fallback, and their comments — no new sink, no ES6 syntax, no timer, no network call.
7. Section 3's extended `_both_tabs_ok_end_to_end()` passed — a real `companion/app.py` subprocess, a real login, a real seeded database and a real `/health` response whose body carried the nested modifier twice, the prose modifier once, both readout spans and no raw ISO in the readout — and what that response actually contained is written into the SUMMARY.
8. The SUMMARY names, explicitly and separately, the pixel-level items still outstanding for the orchestrating session's browser pass, and records finding 5 as OPEN with both candidates, their line references and the trade-off that stops each from being applied blind.
</verification>

<success_criteria>
- Same-row stat tiles match height, the Resolution-statistics description column wraps instead of overflowing, the battery readout reads as a humanised figure plus muted detail in both its resting and its hover/tap/keyboard state, and the page's headings decrease with nesting depth instead of flattening.
- Every fix is built from this stylesheet's existing tokens and this codebase's existing patterns; no new token, size, muted strength or component is introduced.
- `.stat-tile__value` is not resized, and the plan's reasoning for refusing that specific change — 06.6.4 D-09's Display-role retirement and the design skill's four-size contract — is written into the stylesheet where the next reader will find it.
- Both decision reversals (06.6.3's UXA-06, and quick task 260901-tsa's "battery-trend.js not edited" non-goal) are recorded as knowing reversals in the files they affect, not silently applied.
- The `.data-table` no-crop floor survives intact for every table except the one prose table, and the source-order dependency that makes the opt-out work is pinned by a check, not by a comment.
- `role="status"`, the readout id, and every heading id anchor — including `#server-data`, which `history_page.py` links to — are unchanged.
- Every check the four fixes break is retargeted in place; none is deleted.
- `EXPECTED_CHECK_COUNT` moved to the real on-disk baseline plus exactly 5, with the retargets and the live-HTTP extension recorded as no-count-change edits.
- `scripts/run-all-tests.sh` shows only the pre-existing `server/test_poll_loop.py` failure.
- Finding 5 is left explicitly open with a written verdict, two named candidates and the reason neither was applied blind — not quietly closed and not quietly dropped.
</success_criteria>

<commits>
Focused and atomic, matching this session's established style (`git log --oneline -10`), referencing the quick task id rather than a phase-plan number:
- `fix(quick-260901-uzi): stretch same-row stat tiles and demote the nested heading tier`
- `fix(quick-260901-uzi): let the resolution-statistics description column wrap`
- `fix(quick-260901-uzi): humanize the battery readout in both the page and the script`
- `test(quick-260901-uzi): pin the four Health fixes, EXPECTED_CHECK_COUNT +5`
- `docs(quick-260901-uzi): record the Health follow-up fixes and the open Safari disclosure item`
</commits>

<output>
Create `.planning/quick/260901-uzi-fix-4-confirmed-real-bugs-on-the-health-/260901-uzi-SUMMARY.md` when done.
</output>
