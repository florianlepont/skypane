---
phase: quick-260902-iag
plan: 260902-iag
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - companion/static/style.css
  - companion/pages/health_page.py
  - companion/test_status_pages.py
  - .claude/skills/sketch-findings-skypane/SKILL.md
  - .claude/skills/sketch-findings-skypane/references/visual-direction-typography.md
autonomous: true
requirements: [QUICK-260902-iag]

must_haves:
  truths:
    - "This is a developer-confirmed REVERSAL, not a bug report to diagnose. The developer put Settings' `Runway` heading (20px) beside Health's `Unresolved prefixes` heading (16px) in a screenshot, said in their own words that the Settings version is the correct one, was offered exactly two resolutions — revert to 20px everywhere and let the card boundary signal the grouping, or keep 16px and hear the objection first — and explicitly chose the first. There is no open question about WHETHER to revert. The open questions are the two second-order ones this plan's Tasks 2 and 3 answer."
    - "The reversal is scoped to font-size and font-weight ONLY. `.page-section--nested > h2, .battery-trend-section > h2` currently declares three things: `font-size: var(--font-body-size)`, `font-weight: var(--weight-semibold)` (both from 260901-uzi finding 4, the demotion being reversed) and `margin-bottom: var(--space-md)` (from 260902-bl2 bug 2, a spacing fix with an independent justification that the orchestrating session then confirmed live at 16px across all three cards). The first two go; the third stays, and the rule survives holding only that one declaration."
    - "The revert target must be read from source, not assumed. `.text-heading` declares `font-size: var(--font-heading-size)` / `font-weight: var(--weight-regular)` / `line-height: 1.2`; the `h1, h2, h3, legend, .text-heading` rule adds `font-family: var(--font-serif)` / `--weight-regular` / `letter-spacing: -0.01em`; `:root` declares `--font-heading-size: 20px`. Deleting the two overrides therefore lands the nested card headings on 20px serif regular — byte-identically the treatment Settings' own `<h2 class=\"text-heading\">Theme|Runway|Diagnostic LED|Poll</h2>` headings get, which is precisely the match the developer asked for. Confirm all three of those rules on disk before deleting anything."
    - "Every Settings group is a `<section class=\"page-section\">` holding one `<h2 class=\"text-heading\">` — the same bordered-card component, with the same 16px padding, the same `--color-dominant` surface, the same hairline `--color-border` edge and the same heading class that Health's two migrated cards use. That is why the developer's chosen resolution works at all: after this revert, Health's nested card headings and Settings' section headings are literally the same markup under the same rules, differing in exactly one declaration (the retained 16px bottom margin vs the heading-rhythm rule's 8px)."
    - "`.stat-tile__caption`'s semibold promotion (260902-dng Task 3) was justified in writing by a premise this reversal does not merely weaken — it INVERTS. That rule's own comment states the reason as hypothesis (ii): the tile caption and the nested card title are both this file's \"name of a card\" role, and they rendered at two different weights (14px regular serif vs 16px SEMIBOLD serif), which the promotion fixed by making them agree on weight. After this revert the nested card title is 20px REGULAR, so a semibold caption would make the two roles disagree on weight again, in the opposite direction — the smaller role bolder than the larger one. The premise must be re-tested against source and a real verdict reached, not carried forward unexamined."
    - "The default disposition for `.stat-tile__caption` is therefore REVERT (drop the `font-weight` declaration, returning it to `.text-label`'s inherited `--weight-regular`), because that is what the stated justification, re-evaluated, now points at. Keeping the promotion is permitted ONLY if a fresh justification can be written that never references the 16px tier, stands on its own after the revert, and survives the weight-inversion test in Task 2 Step 3. Either outcome ships a written verdict; silently leaving a fix whose only stated reason just evaporated is the one unacceptable outcome."
    - "The hierarchy question the revert opens is real and must be answered with layout inspection, not assertion. Health renders TWO structural levels — the D-10 section headings (`Screen`, `Server & data`) and the cards nested under them (`Battery trend`, `Unresolved prefixes`, `Resolution statistics`) — and after this revert both levels render at 20px serif regular, which is exactly the flattening 260901-uzi finding 4 set out to fix. Settings does NOT have this problem to compare against: Settings is single-level (four sibling cards, no section heading above them), so Settings' precedent proves \"a 20px heading inside a bordered card reads fine\", not \"two levels at 20px read as distinct\". That gap must be closed by real evidence from Health's own DOM and cascade."
    - "That evidence exists in source and is strong, but must be verified rather than taken from this plan. Containment: a level-1 heading lives in a `<div class=\"section-intro\">` on the page canvas — no border, no background, no padding, paired with an inline 14px muted description — while a level-2 heading is the first child of a bordered `--color-dominant` card (`.page-section` or `.battery-trend-section`, both with a 1px `--color-border` edge, `--radius-control` corners and 16px padding). Spacing: `.battery-trend-section`'s `margin-bottom: var(--space-2xl)` (48px) closes a section, `.page-section`/`.dashboard-grid`'s `margin-bottom: var(--space-lg)` (24px) separates cards inside one section, the retained nested-heading rule gives 16px inside a card, and the heading-rhythm rule gives a section-intro 8px — 48 > 24 > 16 > 8, strictly ordered. Adjacency: a `.dashboard-grid` always sits between a level-1 heading and the first level-2 card, so the two tiers are never immediately adjacent on screen. Render the page and read the rules to confirm each of these three before relying on any of them."
    - "If that inspection finds the layout does NOT carry the distinction, the finding must be stated plainly and a non-font-size remedy proposed (spacing, indentation, surface, a level-1 treatment that is not a size). Silently reintroducing a size or weight difference between the two tiers is the exact thing being reversed and is forbidden regardless of what the inspection concludes."
    - "The validated Merged Health Sketch's own answer to this question is a THIRD option, and it is neither 20px nor 16px-semibold: its `.wide-card__caption` card-title role is `font-size: var(--font-label-size)` (14px), muted, uppercase with `.03em` tracking, while its `h2.text-heading, .section-heading` section-heading role is 20px serif regular. The sketch separates the tiers by making the card title a small uppercase eyebrow label. That option is NOT taken here — the developer chose the Settings match explicitly — but it must be recorded as a considered, named alternative so a later \"finish matching the sketch\" edit argues with a written decision instead of discovering an apparent omission."
    - "The sketch's `h2.text-heading, .section-heading` rule also declares `margin: 0 0 var(--space-md)` — 16px below EVERY heading, not just card titles. This stylesheet's heading-rhythm rule declares 8px universally, with the three Health nested cards at 16px as the only exception. That app-wide inconsistency is real, is NOT this task's to fix, and must be handed forward in the SUMMARY rather than quietly widened or quietly closed."
    - "Exactly two harness checks in `companion/test_status_pages.py` assert values this task removes, and both must be retargeted IN PLACE, never deleted: `_nested_heading_tier_demoted_to_emphasis_role()` asserts the demotion rule declares `font-size: var(--font-body-size)` and `font-weight: var(--weight-semibold)`, and `_stat_tile_caption_weight_and_four_role_type_scale_hold()` asserts both the caption's semibold weight and the nested card title's 16px/semibold pair. A repo-wide grep confirms no other harness file references either literal; confirm that yourself before editing."
    - "`_nested_card_heading_rhythm_end_to_end()` and the live-HTTP `_both_tabs_ok_end_to_end()` extension both key on `margin-bottom: var(--space-md)` and the `> p.text-body` prose rhythm rule. Both survive this task untouched, because the margin is deliberately retained — which is itself a check that the reversal stayed scoped. If either needs editing, the reversal has over-reached."
    - "Comment placement is load-bearing and this task is the single most likely one to break it. Both retargeted checks slice a rule's DECLARATION BLOCK (between the braces) and assert on the absence of property names inside it. The new comment recording this reversal necessarily names the properties being removed, so it MUST sit above the selector, outside the braces — this file's universal style. A reasoning comment written inside the braces fails the very check it is explaining."
    - "The design-system skill's record must be checked against reality rather than assumed stale. A grep of `.claude/skills/sketch-findings-skypane/` shows it never documented the 16px nested-heading tier at all (260901-t00 wrote it before 260901-uzi's demotion existed), so there is no reverted-decision-described-as-current to correct there. But `references/visual-direction-typography.md` DOES enumerate `.stat-tile__caption`'s declarations, and that enumeration went stale when 260902-dng added the weight. Verify both facts by grep at execution time and act on what you find, not on this sentence."
    - "`companion/test_status_pages.py` passes with `EXPECTED_CHECK_COUNT` moved from its real on-disk baseline to that baseline plus exactly 1, both retargets done in place, and no check deleted."
    - "`scripts/run-all-tests.sh` reports exactly one failing harness, `server/test_poll_loop.py` (the known, pre-existing, unrelated panel.bin digest mismatch). No harness that passed before this task fails after it."
  artifacts:
    - path: "companion/static/style.css"
      provides: "`.page-section--nested > h2, .battery-trend-section > h2` reduced to its retained `margin-bottom` declaration alone, with a SUPERSEDED record above the selector naming what 260901-uzi's finding 4 did, what the developer chose instead, what now carries the hierarchy, and the sketch's own uppercase-eyebrow alternative as a declined third option; plus `.stat-tile__caption`'s adjudicated verdict recorded in its own comment"
      contains: "260902-iag"
    - path: "companion/pages/health_page.py"
      provides: "The `render()` and `_registry_section()` comments corrected so no comment in the module still claims a demotion to the Emphasis role that no longer exists"
      contains: "260902-iag"
    - path: "companion/test_status_pages.py"
      provides: "Both stale checks retargeted in place onto the reverted values, 1 new check pinning the layout-and-spacing contract that now carries the two-level hierarchy in font-size's place, and `EXPECTED_CHECK_COUNT` at the real on-disk baseline + 1 with a provenance entry"
      contains: "260902-iag"
    - path: ".claude/skills/sketch-findings-skypane/references/visual-direction-typography.md"
      provides: "The `.stat-tile__caption` declaration enumeration brought back into agreement with the shipped rule, and the nested-card-title tier recorded at its current value using the file's own SUPERSEDED convention"
      contains: "260902-iag"
  key_links:
    - from: "the deleted `font-size`/`font-weight` declarations on the nested-heading rule"
      to: "`_nested_heading_tier_demoted_to_emphasis_role()`'s and `_stat_tile_caption_weight_and_four_role_type_scale_hold()`'s declaration-block assertions — both slice that exact rule body and assert those exact literals are PRESENT. Deleting the declarations without retargeting both checks turns a deliberate reversal into two red tests; retargeting only one leaves a check asserting a value this task deliberately removed"
    - from: "the new comment above the nested-heading rule"
      to: "the same two checks' declaration-block slices — the comment names `font-size` and `font-weight` by necessity, and both retargeted checks will assert those property names are ABSENT from the block. A comment written inside the braces instead of above the selector fails both checks at once, for a reason that has nothing to do with the change being made"
    - from: "`.stat-tile__caption`'s weight decision"
      to: "260902-dng's own written justification in that rule's comment — the promotion's ONLY stated reason is the 16px-semibold nested title this task removes. The verdict must be reached by re-reading that comment and testing its premise, not by leaving the declaration in place because no test failed"
    - from: "the retained `margin-bottom: var(--space-md)`"
      to: "`_nested_card_heading_rhythm_end_to_end()` and the live-HTTP stylesheet fetch in `_both_tabs_ok_end_to_end()`, both of which assert that literal. Their staying green untouched is the scope guard proving this reversal took the two typography declarations and nothing else"
    - from: "the reverted 20px nested card headings"
      to: "Settings' `<h2 class=\"text-heading\">` headings inside `<section class=\"page-section\">` — the same markup under the same rules is the whole point of the developer's chosen resolution, so a render-time comparison of the two pages is the real proof the match landed, not a stylesheet read alone"
---

<objective>
Reverse a same-day decision at the developer's explicit instruction: Health's nested card headings (`Battery trend`, `Unresolved prefixes`, `Resolution statistics`) go back to the standard 20px `.text-heading` treatment, matching Settings, with each card's own border/background/padding carrying the "grouped unit" signal that font-size was briefly asked to carry.

| # | What | Why |
|---|------|-----|
| 1 | Delete `font-size: var(--font-body-size)` and `font-weight: var(--weight-semibold)` from `.page-section--nested > h2, .battery-trend-section > h2`; keep `margin-bottom: var(--space-md)` | The developer compared Settings' 20px `Runway` heading against Health's 16px `Unresolved prefixes` heading by screenshot, called the Settings version the correct one, and explicitly chose "revert to 20px everywhere, rely on the card boundary" over "keep 16px and hear the objection" |
| 2 | Re-adjudicate `.stat-tile__caption`'s semibold promotion (260902-dng Task 3) | That promotion's only written justification was matching the weight of the 16px-semibold nested card title. This revert does not weaken that premise, it inverts it. A fix whose stated reason just disappeared does not get to stay unexamined |
| 3 | Verify the two-level hierarchy still reads without a size difference, by real layout inspection | Health has two tiers (section headings vs nested cards); Settings has one. The Settings precedent does not transfer for free, so the containment, spacing and adjacency signals that now carry the distinction must be read from the real DOM and cascade, and pinned |

Purpose: close the developer's own explicit reversal instruction, and leave behind a written record of it that a later "restore the demotion" edit has to argue with.

Output: one stylesheet rule reduced to a single declaration with a SUPERSEDED record above it, one adjudicated verdict on `.stat-tile__caption`, two harness checks retargeted in place, one new harness check pinning what now carries the hierarchy, two corrected comments in `health_page.py`, a corrected design-system record, and a SUMMARY naming exactly what still needs a live-browser pass.

**Approach note — this is a reversal, and it must read as one.** This session has reversed same-day decisions before (260901-uzi reversed 06.6.3's UXA-06 grid alignment; 260902-gjj restored 06.5's D-01 card-edge status intent; 260902-chc reversed D-12). Every one of them left the old rule, the new rule and the reason in writing at the site of the change, and the design-system skill's own `SUPERSEDED` convention exists for exactly this. Follow that pattern here: do not delete 260901-uzi's reasoning, supersede it. A future reader must be able to see that the 16px demotion was tried deliberately, shipped, compared against Settings by the developer, and reversed by the developer's own explicit choice — not that it never existed.

**Non-goals — verified, deliberately NOT touched.**
- **`margin-bottom: var(--space-md)` on the nested-heading rule.** 260902-bl2's bug-2 fix, justified independently of any font size (it makes the heading-to-content gap deterministic regardless of which element type follows), and confirmed live at a uniform 16px across all three cards by the orchestrating session's own browser pass afterwards. It stays, and two existing checks that assert it must stay green untouched.
- **The `> p.text-body` prose rhythm rule.** The other half of the same bl2 fix. Untouched.
- **`.stat-tile__value`.** 16px semibold, the Emphasis role placement 06.6.4 (D-09) made and 260901-uzi finding 4 protected. Not reopened. Whatever Task 2 concludes about the caption, the tile's own datum stays the loudest thing in its tile.
- **The `--font-*` token set and the four-size scale.** No token value changes; no fifth size is introduced; nothing is added to the serif selector.
- **The 8px-vs-16px heading-rhythm inconsistency between Settings and Health's nested cards.** Real, app-wide, and identified during this task's own reading — the sketch declares 16px below every heading while this file declares 8px universally with three Health exceptions. Recorded in the SUMMARY as a future item; NOT resolved here in either direction.
- **The sketch's uppercase-eyebrow card-title treatment (`.wide-card__caption`, 14px muted uppercase).** A genuine third option the sketch itself uses. Recorded as a declined alternative, not adopted — the developer chose the Settings match.
- **Every page other than Health.** Both edited selectors are scoped through `.page-section--nested` and `.battery-trend-section`, classes only `health_page.py` emits, and `.stat-tile__caption`, which `layout.stat_tile()` emits from exactly four call sites, all in `health_page.py` (grep-verified by 260902-dng; re-verify rather than trust). Settings, History, Preview and Airlines are provably untouched.
- **All markup structure.** No element, class, id, heading level, role or live region changes anywhere. Two Python edits in this task are comment corrections only.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./.claude/CLAUDE.md
@.claude/skills/sketch-findings-skypane/SKILL.md
@.planning/quick/260902-bl2-fix-2-more-confirmed-real-bugs-on-the-he/260902-bl2-SUMMARY.md
@.planning/quick/260902-dng-fix-2-confirmed-severe-real-bugs-on-the-/260902-dng-SUMMARY.md

@companion/static/style.css
@companion/pages/health_page.py
@companion/pages/config_page.py
@companion/test_status_pages.py
</context>

<!-- planner-discipline-allow: font-size -->
<!-- planner-discipline-allow: font-weight -->
<!-- planner-discipline-allow: font-family -->
<!-- planner-discipline-allow: var(--weight-semibold) -->
<!-- planner-discipline-allow: var(--font-body-size) -->

<tasks>

<task type="auto">
  <name>Task 1: Return Health's nested card headings to the standard 20px heading treatment</name>
  <files>companion/static/style.css, companion/pages/health_page.py, companion/test_status_pages.py</files>
  <read_first>
    - style.css's `.page-section--nested > h2, .battery-trend-section > h2` rule and its ENTIRE comment block, first character to last. It is a five-paragraph record: four numbered paragraphs from 260901-uzi finding 4 (the measured inverted-hierarchy complaint, why a bigger tile value was refused, what was actually wrong, and what the rule deliberately does not do), a note about the battery heading's icon now being larger than its text at the demoted size, and a fifth paragraph from 260902-bl2 covering the margin. You are about to supersede paragraphs one through four and the icon note, and to KEEP paragraph five. Know which is which before you type anything.
    - style.css's `.text-heading` rule, the `h1, h2, h3, legend, .text-heading` family rule, the `h1, h2, h3, .text-heading` heading-rhythm rule, and `:root`'s `--font-heading-size` / `--font-body-size` / `--weight-regular` / `--weight-semibold` declarations. Confirm for yourself, from the real current file, that deleting the two overrides lands these headings on 20px serif regular — this plan asserts it, but the file has been reworked several times today (260902-dng, 260902-ep7, 260902-gjj) and the file is the authority.
    - `companion/pages/config_page.py`'s `theme_fieldset()`, `runway_fieldset()`, the LED group builder and the Poll section, plus the `<section class="page-section">` wrappers around them. Confirm that every Settings group is the same bordered-card component holding a plain `<h2 class="text-heading">`, and that Settings has NO section heading above those cards — it is single-level. That asymmetry with Health is the thing Task 3 has to deal with, and you should see it here first, in the source.
    - `health_page.py::render()`'s Server & data block, specifically the comment above the Unresolved-prefixes `<section>` that states the nested cards' `<h2>` is demoted "to the Emphasis role", and `_registry_section()`'s comment referring to "the `.page-section--nested > h2` demotion rule's margin-bottom". Both are about to become partly false; find every such claim yourself with a grep for `demot` and `Emphasis` across `companion/`, rather than trusting this list to be complete.
    - `health_page.py::_battery_trend_section_html()`'s emitted `<h2>` — an icon, the heading text, and a trailing `<span class="text-label section-caption">`. At 20px the 20px icon matches the text size again, which is what the demotion rule's icon note was written about; that note becomes obsolete with the reversal.
    - `companion/test_status_pages.py::_nested_heading_tier_demoted_to_emphasis_role()` and `_stat_tile_caption_weight_and_four_role_type_scale_hold()` in full, including their `check(...)` description strings. Both assert on the rule body you are about to empty. Note precisely which of their assertions are markup (still true), which are stylesheet (about to be false), and how each locates a rule body.
    - `companion/test_status_pages.py::_nested_card_heading_rhythm_end_to_end()` and the `margin-bottom: var(--space-md)` needle in `_both_tabs_ok_end_to_end()`'s served-stylesheet loop. Neither should need an edit. If you find yourself editing either, stop — the reversal has taken something it was not asked to take.
    - Grep `companion/` for `page-section--nested > h2`, `--weight-semibold` and `stat-tile__caption` to confirm for yourself that `test_status_pages.py` is the only harness file referencing any of them.
    - The cached Merged Health Sketch at `/Users/florian/.claude/projects/-Users-florian-Projects-skypane--claude-worktrees-airplanes-api-sustainability-a4b703/e1c689bd-9161-44a8-a403-c6b1d0a720e9/tool-results/artifact-3303f9eb-1788256096-c307.html` — its `h2.text-heading, .section-heading` rule and its `.wide-card__caption` rule, in the `<style>` block. The sketch's own card-title answer is a 14px muted uppercase eyebrow, a third option neither this task nor the one it reverses took; read it before recording it as declined.
  </read_first>
  <action>
**A. `style.css` — reduce the rule to its one retained declaration.** Delete `font-size` and `font-weight` from `.page-section--nested > h2, .battery-trend-section > h2`. Keep `margin-bottom: var(--space-md)` and keep both selectors. The rule now exists solely to give a nested card heading a 16px gap below it, and everything else about the heading comes from `.text-heading` and the shared heading rules, exactly as it does on Settings.

**B. `style.css` — rewrite the comment as a reversal record, ABOVE the selector.** This is the substance of the task. Never write any of this inside the braces: two harness checks slice this rule's declaration block and will assert the property names you are about to discuss are absent from it.

Restructure the comment so a reader meets the current state first and the history second. Cover, in this order:

First, what the rule does today and why it is nearly empty: it carries one declaration, the bottom margin, and states no typography at all — a nested card heading is deliberately the same `.text-heading` treatment as every other section heading in the app.

Second, the reversal itself, in the file's own SUPERSEDED voice. 260901-uzi finding 4 demoted this tier from 20px serif regular to 16px semibold, to stop Health's D-10 section headings and the cards nested inside them from rendering at one identical visual tier. That was a real problem and a considered fix; it is reversed here, not deleted, and its own reasoning stays readable in this comment. State what replaced it: the developer put Settings' 20px `Runway` heading beside Health's 16px `Unresolved prefixes` heading in a screenshot, judged the Settings version correct, was offered the explicit choice between reverting to 20px and keeping 16px, and chose to revert. Name the mechanism that now does the job the font size was doing: each card's own boundary — the `--color-border` hairline, the `--color-dominant` surface and the 16px padding that `.page-section` and `.battery-trend-section` already declare — is what signals "this is one grouped unit", the same signal every Settings section relies on and the only signal Settings has ever had.

Third, the two alternatives that were NOT taken, each named so a later edit has to argue rather than discover. The sketch's own card-title role is a 14px muted uppercase eyebrow label (`.wide-card__caption` in the cached artifact) — a genuine third answer to the same hierarchy question, declined because the developer asked specifically for the Settings match. And the demotion itself is declined going forward: restoring a size or weight difference between these two tiers is the thing this reversal exists to undo, so a future contributor who believes the tiers still collide should reach for spacing, surface or containment, not type scale.

Fourth, fold the retained margin's own record (260902-bl2's fifth paragraph) into the new structure, keeping its substance: where the 16px comes from, why longhand rather than the shorthand, and why the pairing with the `> p.text-body` rule below makes the gap deterministic. Do not lose it in the rewrite.

Finally, delete the note about the battery heading's icon being larger than its text at the demoted size — it described a consequence of the demotion and stops being true when the heading returns to 20px. Say in one clause that it was removed for that reason, so its disappearance reads as deliberate.

**C. `health_page.py` — correct every comment that now describes a rule that no longer exists.** In `render()`, the Server & data block's comment states the nested cards' own `<h2>` is demoted to the Emphasis role by `.page-section--nested > h2`. Rewrite that sentence: the modifier is still correct and still additive, and it still marks these two cards as nested inside the section heading above them — but what the modifier now buys is the card's heading rhythm, not a type demotion, and the nesting relationship is expressed by the card boundary. Keep the existing note about why `_source_fault_block()` deliberately does not get the modifier; that reasoning is unaffected. In `_registry_section()`, retarget the phrase naming "the demotion rule" onto whatever that rule now is. Reference this quick task id in both, so the correction is greppable. Fix any other occurrence your `demot`/`Emphasis` grep turned up; do not stop at the two this plan names.

**D. `test_status_pages.py` — retarget both stale checks IN PLACE. Delete neither.**

`_nested_heading_tier_demoted_to_emphasis_role()`: the markup half is entirely unaffected and must not be touched — the two nested cards, the source-fault block's exclusion, and both `.section-intro` headings are all still exactly as asserted. Invert the stylesheet half: the rule must now declare the retained bottom margin and must declare NO font size, NO font weight and (still) NO font family, because a nested card heading is deliberately the standard `.text-heading` treatment. Add the positive half that makes the check meaningful after the reversal: assert `.text-heading` itself still declares the heading size and the regular weight, and that `--font-heading-size` is still 20px in `:root`, so the check fails loudly if the treatment this rule now inherits ever moves. Rename the function and rewrite its `check(...)` description to describe the reversal rather than the demotion, and reference this quick task id in the comment so the retarget's provenance is on the record. Write the failure messages to say what a failure MEANS: a font size or weight reappearing in this block is the reverted demotion returning; a missing bottom margin is 260902-bl2's spacing fix being lost by a revert that over-reached.

`_stat_tile_caption_weight_and_four_role_type_scale_hold()`: fix only its nested-card-title assertions in this task — that role now inherits 20px regular and declares neither of its own. Leave the caption assertions exactly as they are for now; Task 2 owns them and will rewrite this check's whole contract once the caption verdict is reached. The check must be green at the end of THIS task, so make the minimum nested-title correction needed for that and no more.

No `EXPECTED_CHECK_COUNT` movement in this task — both edits are in place.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
s = open('companion/static/style.css').read()
sel = '.page-section--nested > h2,'
at = s.index(sel); open_b = s.index('{', at); close_b = s.index('}', open_b)
sel_list = s[at:open_b]; body = s[open_b:close_b]
assert '.battery-trend-section > h2' in sel_list, 'both nested-card selectors must survive the revert'
assert 'margin-bottom: var(--space-md)' in body, '260902-bl2 spacing fix must be retained — the revert is scoped to typography'
for prop in ('font-size', 'font-weight', 'font-family'):
    assert prop not in body, 'the reverted rule must declare no %s (comments belong ABOVE the selector)' % prop
assert body.count(':') == 1, 'the rule should carry exactly one declaration after the revert'
h = s[s.index('.text-heading {'):]
h_body = h[h.index('{'):h.index('}')]
assert 'font-size: var(--font-heading-size)' in h_body, 'the treatment being reverted TO must still be 20px'
assert 'font-weight: var(--weight-regular)' in h_body, 'the treatment being reverted TO must still be regular'
root = s[s.index(':root'):s.index(':root') + 900]
assert '--font-heading-size: 20px' in root, 'the 20px target token must be unchanged'
comment = s[s.rindex('/*', 0, at):at]
assert '260902-iag' in comment, 'the reversal must be recorded above the selector'
assert 'wide-card__caption' in comment, 'the declined sketch alternative must be named'
print('css ok')
" && server/.venv/bin/python3 -c "
import sys, tempfile, shutil; sys.path.insert(0, '.')
from datetime import timezone, datetime
from companion.pages import health_page as h
from companion.pages import config_page as c
d = tempfile.mkdtemp()
r = h.render({'state_dir': d}); shutil.rmtree(d, ignore_errors=True)
for heading in (h.BATTERY_SECTION_HEADING, h.UNRESOLVED_SECTION_HEADING, h.STATS_SECTION_HEADING):
    assert '>%s' % heading in r, 'expected %r to render' % heading
    at = r.index('>%s' % heading)
    tag = r[r.rindex('<h2', 0, at):at + 1]
    assert 'class=\"text-heading\"' in tag, 'nested card heading %r must be a plain .text-heading now, got %r' % (heading, tag)
src = open('companion/pages/health_page.py').read()
assert '260902-iag' in src, 'health_page.py must record the corrected demotion claims'
import re
for m in re.finditer(r'Emphasis role', src):
    seg = src[max(0, m.start() - 400):m.start()]
    assert 'stat_tile' in seg or 'D-09' in seg or '260902-iag' in seg, 'a stale Emphasis-role claim about the nested tier survives near offset %d' % m.start()
print('markup ok')
" && server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_config_page.py && server/.venv/bin/python3 companion/test_view_pages.py && server/.venv/bin/python3 companion/test_companion_app.py && server/.venv/bin/python3 companion/test_contrast_check.py</automated>
  </verify>
  <done>
`.page-section--nested > h2, .battery-trend-section > h2` carries exactly one declaration — the retained 16px bottom margin — and states no typography, so all three nested Health card headings render at the same 20px serif regular treatment Settings' own section headings use. The comment above the selector records the reversal in the file's SUPERSEDED voice: what 260901-uzi's demotion did and why, that the developer compared it against Settings and explicitly chose to revert, that the card boundary now carries the grouping signal, and that the sketch's own 14px uppercase eyebrow was a considered third option not taken. The obsolete icon-size note is gone and its removal is explained. `health_page.py` no longer contains a comment claiming a demotion that does not exist. Both stale harness checks are retargeted in place, neither deleted, `EXPECTED_CHECK_COUNT` unchanged, and every companion harness is green.
  </done>
</task>

<task type="auto">
  <name>Task 2: Re-adjudicate the stat-tile caption's semibold promotion against the reverted tier</name>
  <files>companion/static/style.css, companion/test_status_pages.py</files>
  <read_first>
    - style.css's `.stat-tile__caption` rule and its ENTIRE comment, first character to last. The 260902-dng paragraph states the promotion's justification explicitly, distinguishes hypothesis (i) from hypothesis (ii), names which one it acted on, and records the rejected Options B and C. This is the primary evidence for the adjudication and you must read the real text rather than any paraphrase.
    - `.planning/quick/260902-dng-fix-2-confirmed-severe-real-bugs-on-the-/260902-dng-PLAN.md`'s Task 3 section and `260902-dng-SUMMARY.md`'s "Task 3 Verdict — The Type-Hierarchy Question" section, in full. The SUMMARY contains the role table as it stood then and the developer's own live confirmation of the promoted caption. Both matter: the first is the reasoning to test, the second is evidence on the other side that must be weighed rather than ignored.
    - style.css's `.text-label` (the caption's inherited size and weight), `.stat-tile__value`, the now-reverted nested-card-heading rule from Task 1, `.text-heading`, and the `h1, h2, h3, legend, .text-heading` family rule. These five are the whole type region under adjudication; build the role table from them directly.
    - `companion/layout.py::stat_tile()`'s emitted caption markup, and a repo-wide grep for `stat_tile(` call sites. 260902-dng's own SUMMARY records that this plan's predecessor overstated the blast radius (11 claimed, 4 real, all in `health_page.py`); re-verify the current number yourself rather than inheriting either figure.
    - `companion/test_status_pages.py::_stat_tile_caption_weight_and_four_role_type_scale_hold()` as Task 1 left it, including its `check(...)` description. Its stated contract — "the caption/value/nested-title trio sharing one weight tier while the section heading alone stays regular" — is itself a casualty of the reversal, since the nested title has left the semibold tier. The check needs a new contract, not a patched assertion.
    - The cached Merged Health Sketch's `.stat-tile__caption` rule, for what the validated artifact itself does with this element (14px muted uppercase with tracking, no weight promotion). Not authoritative given how much has changed since, but it is evidence and should be named in the verdict either way.
  </read_first>
  <action>
**Step 1 — write down 260902-dng's actual stated justification, quoted from its own comment.** Not summarised from this plan. The comment names hypothesis (ii) as the reason acted on: the tile caption and the nested card title are both this file's "name of a card" role, and they rendered at two different weights, which the promotion resolved by making them agree.

**Step 2 — build the real post-revert role table from source.** Four rows: the section heading (`.section-intro`'s `<h2 class="text-heading">`), the nested card title (Task 1's reverted rule), the stat-tile caption, and the stat-tile value. Three columns: size, weight, family — each read from the declarations that actually apply, following the cascade, not from memory. Put this table in the SUMMARY.

**Step 3 — apply two tests to the promotion, and state both results.**

The premise test: does hypothesis (ii)'s premise survive? It asserted the two "card name" roles disagreed on weight and should agree. After the revert the nested card title is regular. So a semibold caption does not restore agreement — it recreates the disagreement in the opposite direction, with the smaller role now the bolder one. Determine whether that reading holds against your own role table, and say so plainly.

The inversion test: after the revert, list which roles in the Server & data region carry semibold. If the answer is "only the two smallest" — the 14px caption and the 16px tile value — while both 20px roles are regular, weight increases as size decreases across the region. Judge whether that is a defensible type system or the same class of inversion this session has repeatedly been asked to fix.

**Step 4 — reach a verdict and ship it. The default is to revert.** If both tests point the same way, drop `font-weight` from `.stat-tile__caption`, returning it to `.text-label`'s inherited regular weight and leaving its size, its named serif exception and its two explicit resets untouched. That outcome matches the principle this whole reversal rests on: let the card boundary and the size scale carry the hierarchy, and keep each text role's own declarations minimal.

Keeping the promotion is permitted, but only under a strict condition: you must be able to write a fresh justification that never references the 16px tier, that stands entirely on the post-revert role table, and that answers the inversion test rather than sidestepping it. If you cannot write that paragraph honestly, the promotion does not survive. Do not keep it merely because 260902-dng's developer-facing confirmation was positive — that confirmation was given while the caption sat beside a 16px semibold title, which is the exact condition being removed.

**Step 5 — record the verdict in the comment, in the file's SUPERSEDED voice.** Keep 260902-dng's reasoning readable; do not delete it. Add this task's paragraph: that the promotion's stated premise was re-tested when the nested tier was reverted, what each test found, what was decided, and — if reverted — that the caption is back to the plain Label role it held before 260902-dng. Name the sketch's own treatment of this element as a data point. Reference this quick task id. Whatever the verdict, the next reader must be able to see that the question was actually re-opened and answered, not left alone because no test happened to fail.

**Step 6 — rewrite the harness check's contract to match what shipped.** `_stat_tile_caption_weight_and_four_role_type_scale_hold()` needs a new stated contract, because its old one ("caption/value/nested-title share one weight tier") describes a world this task and Task 1 have jointly ended. Assert the post-revert truth as a set: the four roles' sizes still form the strictly ordered 14/16/20 progression against the real `:root` token values; the caption declares no size of its own and keeps its serif exception; the tile value keeps its Emphasis-role size and weight; the nested card title and the section heading both declare regular weight or inherit it with no override; and the caption's weight is exactly what you decided in Step 4, asserted explicitly in whichever direction that was. Rename the function if its old name no longer describes it. Update the `check(...)` description string. Reference this quick task id in the comment so a reader can find the adjudication that set these values.

No `EXPECTED_CHECK_COUNT` movement in this task — the edit is in place.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -c "
import sys, re; sys.path.insert(0, '.')
s = open('companion/static/style.css').read()
at = s.index('.stat-tile__caption {')
body = s[s.index('{', at):s.index('}', s.index('{', at))]
comment = s[s.rindex('/*', 0, at):at]
assert '260902-iag' in comment, 'the re-adjudication must be recorded in the caption rule comment'
assert '260902-dng' in comment, 'the superseded reasoning must stay readable, not be deleted'
assert 'font-size' not in body, 'the caption must still declare no size of its own — no fifth size'
assert 'var(--font-serif)' in body, 'the named Label-role serif exception must survive untouched'
semibold = 'font-weight: var(--weight-semibold)' in body
label_body = s[s.index('.text-label {'):]
label_body = label_body[label_body.index('{'):label_body.index('}')]
assert 'font-weight: var(--weight-regular)' in label_body, 'the inherited fallback weight must still be regular'
if not semibold:
    assert 'font-weight' not in body, 'a reverted caption declares no weight at all, it inherits .text-label'
t = open('companion/test_status_pages.py').read()
fn_at = t.index('def _stat_tile_caption')
fn = t[fn_at:t.index('    check(', fn_at)]
assert '260902-iag' in fn, 'the caption check must record that it was revisited by this task'
assert ('var(--weight-semibold)' in fn) == semibold or 'caption_body' in fn, 'the check must assert the caption weight that actually shipped'
print('caption verdict recorded: semibold=%s' % semibold)
" && server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
s = open('companion/static/style.css').read()
at = s.index('.page-section--nested > h2,')
body = s[s.index('{', at):s.index('}', s.index('{', at))]
assert 'font-weight' not in body and 'font-size' not in body, 'Task 1 reversal must still hold'
v = s[s.index('.stat-tile__value {'):]
v = v[v.index('{'):v.index('}')]
assert 'font-size: var(--font-body-size)' in v and 'font-weight: var(--weight-semibold)' in v, 'the tile value stays on D-09 Emphasis role — non-goal'
print('scope ok')
" && server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_view_pages.py && server/.venv/bin/python3 companion/test_contrast_check.py</automated>
  </verify>
  <done>
260902-dng's stated justification was quoted from its own comment, the post-revert four-role table was built from the real cascade, and both the premise test and the inversion test were run and their results written down. A verdict shipped — reverting the promotion by default, or keeping it behind a fresh justification that never cites the 16px tier and answers the inversion test. The caption rule's comment records the re-adjudication alongside, not instead of, 260902-dng's reasoning, and names the sketch's own treatment as a data point. `.stat-tile__caption` still declares no size of its own and keeps its serif exception, and `.stat-tile__value` is untouched. The harness check carries a new contract matching what actually shipped, retargeted in place with no count change, and every companion harness is green.
  </done>
</task>

<task type="auto">
  <name>Task 3: Prove the two tiers still read apart on layout alone, pin it, and correct the design-system record</name>
  <files>companion/test_status_pages.py, .claude/skills/sketch-findings-skypane/SKILL.md, .claude/skills/sketch-findings-skypane/references/visual-direction-typography.md</files>
  <read_first>
    - Render Health yourself, in both the empty and the seeded state, with `health_page.render({'state_dir': <tmpdir>})`, and read the ACTUAL emitted structure of both sections end to end — not a summary of it. You need, for each of the two levels: what element wraps the heading, what classes that wrapper carries, what sits immediately before the heading, and what sits between a level-1 heading and the first level-2 card. Trust what you render over anything in this plan.
    - `health_page.py::_section_intro_html()` and `render()`'s two section blocks. The level-1 headings are id-anchored `<h2 class="text-heading">` elements inside a `<div class="section-intro">` flex row paired with an inline muted description; the level-2 headings are the first child of a bordered `<section>`. Confirm both from source.
    - style.css's `.section-intro`, `.section-intro > p`, `.page-section`, `.battery-trend-section`, `.dashboard-grid` and the heading-rhythm rule. Pull the four real spacing values out of them: what closes a section, what separates two cards inside one section, what sits below a nested card heading after Task 1, and what sits below a `.section-intro` row. Do the ordering arithmetic against `:root`'s own token values; do not assume the ordering this plan claims.
    - `companion/pages/config_page.py`'s four Settings groups again, with the question "does Settings have a level above these cards?" in mind. It does not. That is why the Settings precedent proves less than it appears to, and your verdict has to account for the difference rather than lean on the comparison.
    - `companion/test_status_pages.py`'s `EXPECTED_CHECK_COUNT` and its ENTIRE provenance comment block — read the REAL on-disk value at execution time; this plan deliberately names no number. Read the `check(name, fn)` helper's return-tuple contract and the `_mkstate`/`_ctx`/`_iso`/`_now`/`_seed_*` fixture helpers before writing a new check.
    - The two checks Tasks 1 and 2 retargeted, so your new check complements rather than duplicates them. They pin what the rules DECLARE; the new one pins what the layout DOES.
    - `.claude/skills/sketch-findings-skypane/SKILL.md` and `references/visual-direction-typography.md`, plus a grep of the whole skill directory for `nested`, `demot`, `Emphasis` and `stat-tile__caption`. Establish by grep — not assumption — whether the skill ever documented the 16px nested tier, and whether its `.stat-tile__caption` enumeration matches the rule as Task 2 left it. Act on what the grep actually returns.
  </read_first>
  <action>
**A. Inspect the hierarchy for real and reach a written verdict.** With font-size no longer distinguishing the two tiers, determine from the rendered DOM and the real cascade whether they still read apart. Examine at least these three signals, and say for each whether it holds:

Containment — is a level-1 heading visibly outside any card (canvas surface, no border, no padding) while every level-2 heading is inside a bordered, filled, padded card? Verify by locating each heading's enclosing element in the render and checking its class list against the card rules you read.

Spacing — do the four real gaps form a strict ordering that groups cards under their section (section transition > card-to-card > heading-to-content inside a card > section-intro heading to its own first content)? Compute the ordering from the token values, and state what each number is and which rule produces it.

Adjacency — is a level-1 heading ever immediately followed by a level-2 card heading with nothing between them? Check both sections in the render. If something always intervenes, name it.

Then write the verdict. If the three signals carry the distinction, say so with the evidence, and name which signal is doing most of the work. **If they do not, say that plainly and propose a concrete non-font-size remedy** — more space above a section heading, a different surface or rule beneath it, indentation of the nested cards, an eyebrow/overline treatment on level 1, anything that does not reintroduce a size or weight difference between the two tiers. Proposing is enough; do not implement a remedy in this task without it being the stated verdict, and never resolve the finding by reintroducing a type-scale distinction, which is the exact thing this task reverses.

**B. Add exactly one new harness check pinning what now carries the hierarchy.** Nothing in the suite currently asserts it, and after this reversal it is the whole mechanism. One check, two halves, placed beside the checks Tasks 1 and 2 retargeted.

Markup half, on both the empty and the seeded render: every level-2 heading's enclosing element is a `<section>` carrying a card class (the nested modifier or the battery-trend class), and both level-1 headings' enclosing element is the `.section-intro` row and carries no card class. Locate every heading from its own module constant, never from a positional index.

Stylesheet half: the four spacing values are read out of their own rules by selector and asserted to be the strictly ordered set your Step A arithmetic derived, against `:root`'s real token values — so a future edit that flattens any one of them fails here instead of silently dissolving the distinction that replaced font-size.

Write the failure messages to explain the stakes: this check is what stands in for the type-scale difference quick task 260902-iag removed, so a failure means the two tiers may have stopped reading apart, not merely that a number moved.

**C. Bump the count and record the provenance.** Read the current on-disk `EXPECTED_CHECK_COUNT` and set it to that value plus exactly 1. Do not carry any number from this plan text. Add one provenance entry in the block's established format: name this quick task, name the one check added, and record that Task 1's two retargets and Task 2's contract rewrite were all in-place edits with no count change.

**D. Falsifiability pass.** Mutate the new check so each half asserts on something that does not exist in the source it reads, run the harness, and confirm the output reports exactly that one check as FAIL and nothing else. Then restore it. Do the same for one assertion in each of the two retargeted checks, to confirm the retargets are live and not vacuously true. A check that cannot be observed failing is not a check.

**E. Correct the design-system record.** Act on what your grep found, and record the finding either way — if the skill never documented the 16px tier, say so in the SUMMARY rather than implying a correction was made that was not needed.

In `references/visual-direction-typography.md`, bring the `.stat-tile__caption` line into agreement with the rule as Task 2 left it; that line enumerates the rule's declarations and went stale when 260902-dng added a weight. Add a line for the nested-card-title tier at its current value, using the file's own SUPERSEDED convention to record the round trip: the tier was 20px, was demoted to 16px semibold by 260901-uzi finding 4, and was reverted to 20px by the developer's explicit choice in this quick task, with the card boundary carrying the grouping signal. Note that the sketch's own card-title role is a 14px uppercase eyebrow that this app does not use.

In `SKILL.md`, add or amend only what is needed to stop the design-system reference from describing anything that is no longer true, in its existing voice and at its existing altitude — it is a summary that points at the reference files, so most of the detail belongs in the reference, not here. Reference this quick task id in both files.

**F. Full suite.** Run `scripts/run-all-tests.sh`. The only harness in its FAILED list must be `server/test_poll_loop.py` — the known, pre-existing, unrelated panel.bin digest mismatch. If any other harness fails, or the coverage gate reports a new shortfall, stop and fix it; do not record a green result over a new failure.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 -c "
import re, subprocess, sys
src = open('companion/test_status_pages.py').read()
expected = int(re.search(r'^EXPECTED_CHECK_COUNT = (\d+)', src, re.M).group(1))
assert '260902-iag' in src, 'the provenance block and new check must name this quick task'
out = subprocess.run(['server/.venv/bin/python3', 'companion/test_status_pages.py'], capture_output=True, text=True).stdout
passed, total = map(int, re.findall(r'(\d+)/(\d+)', out)[-1])
assert passed == total == expected, 'printed %d/%d against EXPECTED_CHECK_COUNT %d' % (passed, total, expected)
print('count ok: %d' % expected)
" && server/.venv/bin/python3 -c "
import sys, tempfile, shutil; sys.path.insert(0, '.')
from companion.pages import health_page as h
d = tempfile.mkdtemp()
r = h.render({'state_dir': d}); shutil.rmtree(d, ignore_errors=True)
for sid, heading in ((h.SCREEN_SECTION_ID, h.SCREEN_SECTION_HEADING), (h.SERVER_DATA_SECTION_ID, h.SERVER_DATA_SECTION_HEADING)):
    at = r.index('id=\"%s\"' % sid)
    before = r[max(0, at - 200):at]
    assert 'section-intro' in before, '%r must stay on the canvas-level .section-intro row' % heading
    assert 'page-section--nested' not in before[-80:], '%r must not be inside a nested card' % heading
for heading in (h.BATTERY_SECTION_HEADING, h.UNRESOLVED_SECTION_HEADING, h.STATS_SECTION_HEADING):
    at = r.index('>%s' % heading)
    open_at = r.rindex('<section class=\"', 0, at)
    tag = r[open_at:r.index('>', open_at) + 1]
    assert ('page-section--nested' in tag) or (h.BATTERY_SECTION_CLASS in tag), '%r must sit inside a bordered card, got %r' % (heading, tag)
s = open('companion/static/style.css').read()
def decl(sel, prop):
    at = s.index(sel); b = s[s.index('{', at):s.index('}', s.index('{', at))]
    import re as _re
    return _re.search(prop + r':\s*var\(--([a-z0-9-]+)\)', b).group(1)
tok = {'space-sm': 8, 'space-md': 16, 'space-lg': 24, 'space-2xl': 48}
section_gap = tok[decl('.battery-trend-section {', 'margin-bottom')]
card_gap = tok[decl('.page-section {', 'margin-bottom')]
head_gap = tok[decl('.page-section--nested > h2,', 'margin-bottom')]
assert section_gap > card_gap > head_gap, 'the spacing tiers that now carry the hierarchy must stay strictly ordered: %d/%d/%d' % (section_gap, card_gap, head_gap)
print('layout hierarchy ok: %d > %d > %d' % (section_gap, card_gap, head_gap))
" && server/.venv/bin/python3 -c "
skill = open('.claude/skills/sketch-findings-skypane/SKILL.md').read()
ref = open('.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md').read()
assert '260902-iag' in skill or '260902-iag' in ref, 'the design-system record must cite this task'
assert '260902-iag' in ref, 'the typography reference is where the tier record belongs'
assert 'SUPERSEDED' in ref, 'the round trip must use the file own supersede convention'
print('skill record ok')
" && server/.venv/bin/python3 companion/test_config_page.py && server/.venv/bin/python3 companion/test_view_pages.py && server/.venv/bin/python3 companion/test_companion_app.py && server/.venv/bin/python3 companion/test_contrast_check.py && scripts/run-all-tests.sh > /tmp/skypane-iag-run-all-tests.log 2>&1; test "$(sed -n '/FAILED harnesses/,$p' /tmp/skypane-iag-run-all-tests.log | grep -c '^    - ')" = 1 && sed -n '/FAILED harnesses/,$p' /tmp/skypane-iag-run-all-tests.log | grep -q 'server/test_poll_loop.py'</automated>
    <human-check>
REQUIRED, not optional — but do NOT block plan completion on it. This project's memory records that computed-style and structural checks alone have already missed a real rendered bug (`feedback_real_device_ui_verification`), and the last eight Health quick tasks (260901-tsa, 260901-uzi, 260902-bl2, 260902-chc, 260902-dng, 260902-ep7, 260902-gjj and their siblings) each had no browser-automation tooling bound to their executor and handed this pass back to the orchestrating session, which performed it successfully every time. Assume the same division of labour: complete every automated half yourself, then hand the pixel-level items back.

Name these in the SUMMARY as outstanding for the orchestrating session's browser pass:

1. Does the page read with a coherent hierarchy now, and does nothing look randomly oversized? Specifically: with `Battery trend`, `Unresolved prefixes` and `Resolution statistics` back at 20px, do they still read as subordinate to `Screen` and `Server & data`, or do the two levels now read as peers? This is the developer's own accepted trade and the single most important thing to look at.
2. The direct comparison that started this: Settings' `Runway` heading beside Health's `Unresolved prefixes` heading. They should now be indistinguishable in treatment. If they are not, the reversal is incomplete and the difference must be measured, not guessed.
3. Whichever way Task 2 decided the caption: does the stat-tile caption read correctly beside its own tile value and beside the restored 20px card titles? If the promotion was reverted, confirm the captions do not now read as weak or lost; if it was kept, confirm the 14px caption does not read louder than the 20px card title beside it.
4. Both themes, and a narrow viewport. Neither was re-checked after 260902-bl2 (the orchestrating session's tooling failed on those passes), so they are doubly overdue.
5. Nothing else moved: Settings, History, Preview and Health's own source-fault block keep their previous heading treatment, and the 16px heading-to-content rhythm inside all three nested cards is unchanged from the 260902-bl2 pass that was already confirmed live.
6. Still open and not touched here: the Safari readings-disclosure header clipping (260901-uzi finding 5), and the app-wide 8px-vs-16px heading-rhythm inconsistency this task identified but deliberately did not resolve.

Record what was actually observed rather than restating this list as if performed.
    </human-check>
  </verify>
  <done>
The two-tier hierarchy was inspected against the real rendered DOM and the real cascade — containment, spacing ordering and adjacency each checked individually — and a written verdict shipped, with a concrete non-font-size remedy proposed if the signals were found insufficient. One new harness check pins both halves of that mechanism and was observed failing under mutation before being restored, as were the two retargeted checks. `EXPECTED_CHECK_COUNT` is the real on-disk baseline plus exactly 1, with a provenance entry recording the one addition and three in-place edits. The design-system record no longer describes anything untrue: the typography reference's `.stat-tile__caption` enumeration matches the shipped rule and the nested-card-title tier's full round trip is recorded under the file's own SUPERSEDED convention. `scripts/run-all-tests.sh` lists exactly one failing harness, `server/test_poll_loop.py`, and the SUMMARY names the pixel-level items outstanding.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser -> `GET /static/style.css` | A pre-auth static asset. This task deletes two typography declarations from one rule, may delete a third from another, and rewrites comments. It introduces no dynamic content and no new selector. |
| browser -> `GET /health` | Server-rendered HTML for an authenticated operator. This task changes no markup at all — the two Python edits are comment corrections. |
| repo -> `.claude/skills/sketch-findings-skypane/` | A Claude-discoverable design-system reference auto-loaded during UI implementation. Stale content here misleads future automated work, which is why the correction is in scope rather than deferred. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-iag-01 | Repudiation | The reversal itself losing its record | medium | mitigate | A same-day reversal with no written trace invites a later contributor to "fix" the flattening again and re-derive the demotion from scratch. Task 1 requires the superseded reasoning to stay readable beside the new decision, in the file's own SUPERSEDED voice; Task 3 requires the same in the design-system reference; both are asserted by verify gates that grep for this task's id. |
| T-iag-02 | Tampering | Scope creep beyond the two typography declarations | high | mitigate | The retained `margin-bottom: var(--space-md)` and the `> p.text-body` prose rhythm rule are 260902-bl2's independently justified, live-confirmed spacing fix. Task 1's gate asserts the margin survives and that the rule carries exactly one declaration; `_nested_card_heading_rhythm_end_to_end()` and the live-HTTP stylesheet fetch both assert the same literal and must stay green with no edit. |
| T-iag-03 | Denial of Service | Hierarchy/readability regression once font-size stops distinguishing the tiers | high | mitigate | Task 3 requires real layout inspection of containment, spacing ordering and adjacency, a written verdict, and a non-font-size remedy proposal if the signals fail. One new harness check pins the spacing ordering and the containment fact so a later edit cannot silently dissolve what replaced the type distinction. |
| T-iag-04 | Repudiation | A fix surviving whose only stated justification was removed | medium | mitigate | `.stat-tile__caption`'s promotion is adjudicated in Task 2 against 260902-dng's own quoted reasoning, with an explicit default (revert) and a strict condition for keeping it (a fresh justification that never cites the reverted tier). The verify gate asserts a verdict was recorded and that the harness check asserts whatever actually shipped. |
| T-iag-05 | Tampering | A retargeted check silently asserting nothing | medium | mitigate | Both retargets invert or replace assertions rather than deleting them, and Task 3's falsifiability pass requires each of the three touched/new checks to be observed failing under mutation before being restored. |
| T-iag-06 | Tampering | Comment text breaking the checks that read declaration blocks | medium | mitigate | The new comments necessarily name the properties being removed, and both retargeted checks slice the rule's declaration block and assert those names are absent. Task 1 mandates comments above the selector, this file's universal style, and the gate asserts the block contains exactly one declaration and none of the three property names. |
| T-iag-SC | Tampering | npm/pip/cargo installs | n/a | accept | No package-manager install of any kind. This task edits one stylesheet, one Python module's comments, one harness and two Markdown records, all stdlib-only, with no dependency change. |
</threat_model>

<verification>
1. `server/.venv/bin/python3 companion/test_status_pages.py` — all checks pass; the printed total equals the new `EXPECTED_CHECK_COUNT`, which is the real on-disk baseline plus exactly 1.
2. `companion/test_config_page.py`, `companion/test_view_pages.py`, `companion/test_companion_app.py` and `companion/test_contrast_check.py` — all pass at their own unchanged `EXPECTED_CHECK_COUNT`s, proving the reversal reached no other page.
3. `scripts/run-all-tests.sh` — exactly one harness in the FAILED list, `server/test_poll_loop.py` (known pre-existing panel.bin digest mismatch). Coverage gate reports no new shortfall.
4. `git diff --stat` touches only `companion/static/style.css`, `companion/pages/health_page.py`, `companion/test_status_pages.py` and the two design-system Markdown files. No other page module, no JavaScript, no `layout.py`.
5. `git diff companion/static/style.css` shows two deleted declarations on the nested-heading rule (plus possibly one on `.stat-tile__caption`) and comment rewrites — and nothing else. No new selector, no new token, no new size, no changed spacing value, no `:has()`.
6. `git diff companion/pages/health_page.py` shows comment changes only — zero changes to any emitted string, class list, or control flow.
7. `_nested_card_heading_rhythm_end_to_end()` and `_both_tabs_ok_end_to_end()` appear in no diff hunk: the 260902-bl2 spacing fix and its live-HTTP proof are untouched, which is the scope guard.
8. The SUMMARY records the post-revert four-role type table, both Task 2 test results and the verdict, the Task 3 hierarchy verdict with its three signals, and the pixel-level items still outstanding for the orchestrating session's browser pass.
</verification>

<success_criteria>
- All three nested Health card headings render at the same 20px serif regular treatment as Settings' own section headings — the developer's explicitly chosen resolution — with each card's border, surface and padding carrying the grouping signal.
- The reversal is recorded, not concealed: 260901-uzi finding 4's reasoning stays readable beside the developer's decision to reverse it, in the stylesheet, in `health_page.py`'s corrected comments, and in the design-system reference under its own SUPERSEDED convention.
- The 260902-bl2 spacing fix survives intact and provably untouched, and its two existing harness checks stay green with no edit.
- `.stat-tile__caption`'s promotion was genuinely re-adjudicated against 260902-dng's own quoted justification, with both the premise test and the inversion test run and recorded, and a verdict shipped in whichever direction the evidence pointed — not left in place because nothing failed.
- The two-tier hierarchy was verified by real layout inspection with a written verdict, and no font-size or font-weight distinction between the tiers was reintroduced under any circumstances.
- Every check that asserted a value this task removes was retargeted in place; none was deleted; each was observed failing under mutation.
- The design-system skill no longer describes any reverted decision or stale declaration list as current.
- `scripts/run-all-tests.sh` shows only the pre-existing `server/test_poll_loop.py` failure.
</success_criteria>

<commits>
Focused and atomic, matching this session's established style (`git log --oneline -10`), referencing the quick task id rather than a phase-plan number. Because this is a deliberate reversal of a same-day decision, each message states plainly what the old rule was, what replaced it, and why:
- `fix(quick-260902-iag): restore the standard 20px heading on Health's nested cards` — body naming 260901-uzi finding 4's 16px semibold demotion as the reversed decision and the developer's Settings comparison as the reason
- Task 2, whichever way it lands: `refactor(quick-260902-iag): return the stat-tile caption to its inherited regular weight` — or, if the promotion survives on a fresh justification, `docs(quick-260902-iag): re-justify the stat-tile caption's weight after the tier reversal`
- `test(quick-260902-iag): pin the layout-carried hierarchy, EXPECTED_CHECK_COUNT +1`
- `docs(quick-260902-iag): correct the design-system record for the reverted heading tier`
- `docs(quick-260902-iag): record the nested-card heading reversal`
</commits>

<output>
Create `.planning/quick/260902-iag-revert-the-health-nested-card-heading-de/260902-iag-SUMMARY.md` when done.

Beyond the standard sections it must contain, under findable headings: the post-revert four-role type table (size/weight/family for the section heading, nested card title, stat-tile caption and stat-tile value, read from the real cascade); the Task 2 adjudication with both test results and the verdict; the Task 3 hierarchy verdict with all three signals stated individually and any proposed non-font-size remedy; the grep finding on whether the design-system skill ever documented the 16px tier; the app-wide 8px-vs-16px heading-rhythm inconsistency handed forward as a future item; and a "Pixel-Level Items Outstanding" section reproducing the live-browser list for the orchestrating session's pass.
</output>
