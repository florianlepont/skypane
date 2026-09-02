---
phase: quick-260901-qif
plan: 260901-qif
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - companion/static/style.css
  - companion/pages/config_page.py
  - companion/test_config_page.py
autonomous: true
requirements: [QUICK-260901-qif]

must_haves:
  truths:
    - "The three Settings groups (Theme, Runway, Diagnostic LED — all three `.theme-status`-wrapped) render as cards with the SAME box treatment `.page-section` already gives the Poll section on that same page: `--color-dominant` surface, a 1px `--color-border` hairline at rest, `--radius-control` corners, no resting shadow, and `--shadow-card-hover` revealed only on hover/focus-within with the hairline cleared to transparent."
    - "The Diagnostic LED checkbox renders as a normal ~16x16 native checkbox tinted by the existing site-wide `accent-color`, NOT as the 44x44 filled, bordered, rounded box the global `input, select` rule (written for text inputs and selects) was giving it because the element carried no class of its own."
    - "The LED control's activation target is still at least 44px tall: the 44px floor moves onto the wrapping `<label class=\"led-checkbox\">` (the element a native checkbox label already makes clickable), the same relocation-not-removal principle `.copy-btn` uses with its `::before` hit area. The 44px floor register comment above the base `button` rule stays truthful — this control is NOT a new floor opt-out."
    - "The three runway cards lay out as a horizontal, wrapping row inside a new `.runway-row` flex container instead of three full-width blocks stacked one per line; each card is `flex: 1 1 150px` with a `min-width: 140px` floor, and `.runway-row`'s `gap` (not a per-card `margin-bottom`) is the single owner of inter-card and wrapped-row spacing."
    - "`.runway-card`'s own visual treatment is byte-identical to before: same background, same hairline border, same `border-radius`, same `box-shadow: none`, same padding, same cursor, same `:not(.runway-card--selected)` hover/focus-within rule, same `--selected` 2px accent border, same `__number`/`__image`/`__check` rules. Only its container's layout mode and its own flex sizing changed."
    - "`.theme-status__row`, `.theme-swatch`, and `.theme-swatch__chip` are untouched."
    - "Every value used comes from this stylesheet's own existing token set and idioms — `var(--color-dominant)`, `var(--color-border)`, `var(--radius-control)`, `var(--shadow-card-hover)`, `var(--space-sm)` — plus the two literal pixel figures the layout genuinely needs (the 16px checkbox box and the 150px/140px card flex sizing). No new CSS custom property is introduced."
    - "`accent-color` is still declared exactly once in the whole stylesheet, in the global `input, select` rule (D-06's site-wide native-control tint). The new LED rule deliberately does not clear it and does not restate it — one concept, one declaration site."
    - "`companion/test_config_page.py` passes, with `EXPECTED_CHECK_COUNT` moved from its real on-disk baseline to that baseline plus exactly 3 — one check for the `.runway-row` containment/ordering, one for the `led-checkbox` label class and the unchanged input attribute sequence, and one cross-file DOM-contract guard proving style.css actually styles the class names this page module now emits."
    - "`_runway_fieldset_returns_single_top_level_div()` was retargeted IN PLACE (no count change) from `exactly one <div> pair` to `exactly two <div> pairs — the top-level .theme-status wrapper and the nested .runway-row layout container`, with its `startswith`/`endswith` assertions untouched because those are the ones that actually prove D-01's single-top-level-element invariant."
    - "`scripts/run-all-tests.sh` reports exactly one failing harness, `server/test_poll_loop.py` (the known, pre-existing, unrelated digest mismatch). No harness that passed before this task fails after it."
  artifacts:
    - path: "companion/static/style.css"
      provides: "`.theme-status` card treatment + its hover/focus-within pair; `.runway-row` flex container; `.runway-card` flex sizing (margin-bottom retired); `.led-checkbox` 44px flex label + `.led-checkbox input[type=\"checkbox\"]` global-rule opt-out"
      contains: ".runway-row {"
    - path: "companion/pages/config_page.py"
      provides: "`runway_fieldset()` wrapping its cards in a single `<div class=\"runway-row\">`; `led_group()` emitting `<label class=\"led-checkbox\">`"
      contains: "runway-row"
    - path: "companion/test_config_page.py"
      provides: "3 new checks (runway-row containment, led-checkbox label class, cross-file style.css DOM-contract guard), the in-place retarget of the single-top-level-div check, and EXPECTED_CHECK_COUNT at on-disk-baseline + 3"
      contains: "runway-row"
  key_links:
    - from: "`config_page.runway_fieldset()`'s new `<div class=\"runway-row\">` wrapper"
      to: "style.css's `.runway-row` flex rule — the wrapper is inert markup without the rule, and the rule is dead CSS without the wrapper; the Task 3 cross-file guard is what keeps the pair from drifting"
    - from: "`config_page.led_group()`'s new `class=\"led-checkbox\"` on the `<label>`"
      to: "style.css's `.led-checkbox input[type=\"checkbox\"]` rule, whose `min-height: 0` / `min-width: 0` are the only thing that lets the 16px sizing beat the global `input, select` rule's 44px minimums"
    - from: "style.css's `.theme-status` rule"
      to: "style.css's `.page-section` rule — the two now declare an identical box on the same page and must be edited together"
    - from: "`.runway-row`'s `gap: var(--space-sm)`"
      to: "`.runway-card`'s retired `margin-bottom: var(--space-md)` — the gap replaces the margin as the single owner of card spacing; keeping both would stack 16px under every card on top of the 8px gap"
---

<objective>
Fix 3 confirmed visual gaps on the companion Settings page (`/settings`), found during phase 06.6.4.1's closing checkpoint by diffing the real rendered page against the validated Settings Page Sketch.

| # | Gap | Root cause | Fix |
|---|-----|------------|-----|
| 1 | Theme/Runway/LED groups render as unbounded canvas-coloured regions next to a properly-carded Poll section on the same page | `.theme-status` (the shared wrapper all three groups use) only ever got `padding` + `margin-bottom` — it was never given the card treatment every `.page-section` on this site carries | Add the four card declarations `.page-section` already states, plus the same hover/focus-within pair |
| 2 | The Diagnostic LED checkbox renders as an oversized 44x44 filled, bordered, rounded box | The `<input type="checkbox" name="led_enabled">` in `led_group()` carries no class at all, so it inherits the global `input, select` rule written for text inputs and selects | A new `.led-checkbox` label class + a scoped `input[type="checkbox"]` rule that opts out of that global rule declaration by declaration |
| 3 | The 3 runway cards stack one-per-line at full width | The cards are bare siblings of the `<h2>` and both `<p>`s inside `.theme-status`, so each `display: block` card takes a full line | A new `.runway-row` flex container around just the cards, plus flex sizing on the card itself |

Purpose: close the last three visual deltas between the shipped Settings page and its validated sketch, so phase 06.6.4.1's closing checkpoint can sign off on the page as built rather than as intended.

Output: three style.css rule groups (one edited, three added), two markup edits in `config_page.py`, one in-place test retarget, and three new harness checks.

**Approach note — reuse, never invent.** Every treatment here already exists in `companion/static/style.css` and is copied declaration-for-declaration from the rule that established it: the card box from `.page-section`, the hover/focus-within pair from `.page-section:hover`, the 44px-floor-on-a-flex-row from `summary`, the minimum-clearing opt-out from `.filter-bar__field input`, the explicit `background: none; border: none; border-radius: 0` reset from `.filter-bar [data-filter-clear]`, and `flex: none` from `.icon` / `.banner::before`. Do not invent a new token, a new muted strength, a new radius, or a new shadow.

**Non-goals.** Do not touch `.theme-status__row`, `.theme-swatch`, or `.theme-swatch__chip` (already correct). Do not change `.runway-card`'s visual treatment — background, border, radius, shadow, padding, cursor, the `:not(.runway-card--selected)` hover rule, the `--selected` modifier, and the `__number`/`__image`/`__check` rules all stay exactly as they are. Do not reintroduce a `.config-form` column rule in the >=960px block (06.6.4.1 D-01 removed it outright and its comment says so). Do not restate `accent-color` anywhere. Do not touch `handle_post()`.

**Note on the sketch.** The Settings Page Sketch is not an on-disk artifact under `.planning/sketches/` (only 001-health, 002-mobile-nav, 003-history-density are). Its validated target values are therefore stated inline in the tasks below and are the authority for this plan.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./.claude/CLAUDE.md

@companion/static/style.css
@companion/pages/config_page.py
@companion/test_config_page.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Give .theme-status the card treatment .page-section already carries</name>
  <files>companion/static/style.css</files>
  <read_first>
    - The `.page-section` rule and the `.page-section:hover, .page-section:focus-within` pair immediately after it (near the end of the file, just before `.page-section.banner--anomaly`). This is the rule being matched declaration-for-declaration — read its exact declarations and their order before editing anything.
    - The `.theme-status` rule and the comment block directly above it (in the forms/theme-picker neighbourhood, right after `.theme-form .theme-option:not(.theme-option--active):hover` and right before `.theme-status__row`).
    - The file's own header comment paragraph on the 06.6.4 D-03 card contract ("all six card components ... carry a --color-border hairline at rest and reveal --shadow-card-hover only on hover/focus-within").
  </read_first>
  <action>
Edit the `.theme-status` rule in place. It currently declares only `padding: var(--space-md);` and `margin-bottom: var(--space-lg);`. Keep both unchanged — they already equal `.page-section`'s own values, so after this edit the two rules describe an identical box. Add the four card declarations `.page-section` states, using the same property order that rule uses: the `--color-dominant` card surface, a 1px `--color-border` hairline, `--radius-control` corners, and an explicitly-none resting shadow.

Immediately after that rule, add a `.theme-status:hover, .theme-status:focus-within` rule whose body is exactly the two declarations the `.page-section:hover, .page-section:focus-within` pair uses: clear the hairline to transparent, and reveal `var(--shadow-card-hover)`.

Do not add a resting shadow, a transition, or a transform. The 06.6.4 D-03 contract this file's header comment states is hairline-at-rest with the shadow revealed only on hover/focus-within, and `.page-section` — the sibling card this group sits beside on the very same page — declares no transition either, so adding one here would make the two cards animate differently.

Rewrite the head comment above the rule. Its current text explains that a bare `div` inherits none of `fieldset`'s box styling and that padding/margin are restated to avoid a collapse to zero spacing. That premise is still true but it is not the whole story and it is why this gap survived: the wrapper was given back only the spacing the removed `fieldset` used to provide and never the card treatment every `.page-section` on the site carries, so the Theme, Runway and Diagnostic LED groups rendered as unbounded canvas-coloured regions directly beside a properly-carded Poll section. State that, name `.page-section` as the rule this one is now matched against declaration-for-declaration, and say the two must be edited together if either changes.

Leave `.theme-status__row`, `.theme-swatch` and `.theme-swatch__chip` completely untouched.
  </action>
  <verify>
    <automated>test "$(awk '/^\.theme-status \{/,/^\}/' companion/static/style.css | grep -cE 'var\(--color-dominant\)|var\(--color-border\)|var\(--radius-control\)|box-shadow: none')" = 4 && test "$(grep -c '^\.theme-status:hover,' companion/static/style.css)" = 1 && test "$(awk '/^\.theme-status:hover,/,/^\}/' companion/static/style.css | grep -c 'var(--shadow-card-hover)')" = 1 && server/.venv/bin/python3 companion/test_config_page.py</automated>
  </verify>
  <done>
`.theme-status` declares the same six-property box `.page-section` does (surface, hairline, radius, no resting shadow, `--space-md` padding, `--space-lg` bottom margin), its hover/focus-within pair clears the hairline and reveals `--shadow-card-hover`, the swatch rules are unchanged, and `companion/test_config_page.py` still passes at its unchanged `EXPECTED_CHECK_COUNT`.
  </done>
</task>

<task type="auto">
  <name>Task 2: Normalize the LED checkbox and lay the runway cards out in a wrapping row</name>
  <files>companion/static/style.css, companion/pages/config_page.py, companion/test_config_page.py</files>
  <read_first>
    - The global `input, select` rule (in the forms neighbourhood, right after the `label` rule) — every declaration it makes is one this task's scoped rule has to undo, so read all of them.
    - The 44px touch-target floor register comment directly below it, above the base `button` rule. It is an exhaustive audit of who kept and who gave up the floor, and this task must keep it truthful.
    - `.filter-bar__field input` and its comment (the `min-height: 0` load-bearing precedent), and `.filter-bar [data-filter-clear]` (the explicit `background: none; border: none; border-radius: 0` reset idiom).
    - The `summary` rule (`cursor: pointer; min-height: 44px; display: flex; align-items: center;`) — the exact idiom this task reuses to keep the 44px floor on a label.
    - `.icon` and `.banner::before` for the `flex: none` precedent and its stated reason.
    - The whole runway picker block: the comment above `.runway-card`, the rule itself, its `:not(.runway-card--selected)` hover/focus-within rule, `.runway-card--selected`, `.runway-card__number`, `.runway-card__image`, `.runway-card__check`, and `.runway-card--selected .runway-card__check`.
    - `config_page.py`'s `runway_fieldset()` and `led_group()` in full, including their docstrings.
    - `companion/test_config_page.py`'s `_runway_fieldset_returns_single_top_level_div()` — this check WILL fail the moment the row wrapper lands, and retargeting it is part of this task, not Task 3.
  </read_first>
  <action>
**A. LED checkbox — markup.** In `led_group()`, add the class `led-checkbox` to the opening `<label>` tag so it reads as a classed label. Change nothing else in that string: the `<input>`'s attribute sequence (`type`, then `name`, then `value`, then the conditional checked flag) must stay byte-identical, because this harness and the live-HTTP checks match on that exact sequence. Leave the label's text and the single space before it alone.

**B. LED checkbox — CSS.** Add two rules to `companion/static/style.css`, placed immediately after the `.runway-card--selected .runway-card__check` rule and before the data-table section comment, so all three Settings-form layout components end up in one contiguous neighbourhood.

The first rule, `.led-checkbox`, makes the label a centred flex row with `var(--space-sm)` between its two children and a `min-height` of 44px. Comment it: this is `summary`'s own idiom reused verbatim, and the 44px is deliberate — a native checkbox's label is already a click target, so putting the floor here means the control's real activation target stays 44px tall while its painted box shrinks to 16px. That is a relocation of the floor, exactly like `.copy-btn`'s synthesized `::before` hit area, NOT a fourth entry for the floor register's opt-out list; say so, and add a one-line cross-reference to that register comment so a future auditor reading it finds this rule. Note also that `gap`, not the literal space in the markup, is what separates the box from its text once the label is a flex container, and that the flex row is only possible because this rule overrides the global block-level `label` rule.

The second rule, `.led-checkbox input[type="checkbox"]`, undoes the global `input, select` rule for this one control: a 16px square box, both of that rule's 44px minimums cleared to zero, padding cleared to zero, and the surface, edge and corner rounding all explicitly reset the way `.filter-bar [data-filter-clear]` resets its own inherited button chrome. Add `flex: none` for the reason `.icon` and `.banner::before` already state — without it the 16px box shrinks under the flex row's default shrink behaviour. Comment the block: each declaration corresponds to one declaration of the global rule, which is written for text inputs and selects and was reaching this element only because it carried no class of its own — that is the entire reason it painted as an oversized filled box. Call out that the two cleared minimums are load-bearing for the same reason `.filter-bar__field input`'s own cleared minimum is: a browser never lets a plain width or height shrink an element below a minimum another rule sets unless that minimum is itself cleared, so without them the 16px sizing is inert. Finally, record that this rule deliberately neither clears nor restates the native-control tint the global rule declares once site-wide (D-06) — restating it here would create a second place one value lives, which is the exact failure mode this file's `--color-destructive` comment already documents.

**C. Runway row — markup.** In `runway_fieldset()`, wrap the joined card markup in a single `<div class="runway-row">` ... `</div>`, positioned between the description paragraph and the helper-text paragraph, still inside the one top-level `.theme-status` div. The `<h2>`, the description `<p>` and the helper `<p>` all stay outside the row — only the cards go in.

Extend the function's docstring with a short paragraph: the cards used to be bare siblings of the heading and both paragraphs inside `.theme-status`, so each block-level card took a full line and the group rendered as three stacked full-width bars instead of the validated row-of-three. The row is a layout container only — it carries no visual treatment of its own, and the cards keep theirs.

**D. Runway row — CSS.** Add a `.runway-row` rule immediately before the runway-picker comment that heads `.runway-card`: a wrapping flex row with `var(--space-sm)` between items. Comment it as a layout-only container introduced for the cards, and note that its gap is now the single owner of both inter-card and wrapped-row spacing.

Then, in `.runway-card` itself, replace its `margin-bottom` declaration with two flex-sizing declarations: grow-and-shrink from a 150px basis, and a 140px `min-width` floor. The margin goes because `.runway-row`'s gap replaced it; leaving both would stack a 16px margin under every card on top of the 8px gap. Note in the comment that `.runway-card` has exactly one emitter in the repository — `runway_fieldset()`, confirmed by grep — so retiring the margin cannot affect another consumer. Every other declaration in that rule stays byte-identical, and none of the sibling `.runway-card*` rules are touched.

**E. Retarget the now-broken structural check IN PLACE.** `_runway_fieldset_returns_single_top_level_div()` asserts that `runway_fieldset()`'s output contains exactly one opening-div and one closing-div occurrence. The row wrapper makes that two of each, so update both counts to two and reword the failure message and the `check(...)` description to say: exactly two div pairs — the top-level `.theme-status` wrapper and the nested `.runway-row` layout container. Leave the `startswith` and `endswith` assertions exactly as they are; those are the ones that actually prove D-01's single-top-level-element invariant. Add a comment recording that the count moved from one to two because a nested layout container was introduced, and that the original wording about nested divs was a proxy for the top-level invariant rather than the invariant itself.

This is a retarget in place, matching this file's own established discipline for markup-shape changes. `EXPECTED_CHECK_COUNT` does NOT move in this task — Task 3 owns that.
  </action>
  <verify>
    <automated>test "$(awk '/^\.runway-row \{/,/^\}/' companion/static/style.css | grep -cE 'display: flex|flex-wrap: wrap|gap: var\(--space-sm\)')" = 3 && test "$(awk '/^\.runway-card \{/,/^\}/' companion/static/style.css | grep -cE 'flex: 1 1 150px|min-width: 140px')" = 2 && test "$(awk '/^\.led-checkbox \{/,/^\}/' companion/static/style.css | grep -c 'min-height: 44px')" = 1 && test "$(awk '/^\.led-checkbox input\[type="checkbox"\] \{/,/^\}/' companion/static/style.css | grep -cE 'min-height: 0|min-width: 0|width: 16px|height: 16px')" = 4 && test "$(grep -c '^  accent-color: var(--color-accent);' companion/static/style.css)" = 1 && server/.venv/bin/python3 -c "import sys; sys.path.insert(0, '.'); from companion.pages import config_page as c; h = c.render({'device_config': {'theme': 'sky', 'tracked_runway': '3', 'led_enabled': True}, 'poll_cooldown_remaining': 0}); assert h.count('<div class=\"runway-row\">') == 1; assert h.count('<label class=\"led-checkbox\">') == 1; assert h.count('<label class=\"runway-card') == 3; assert h.index('<div class=\"runway-row\">') < h.index('<label class=\"runway-card'); print('markup ok')" && server/.venv/bin/python3 companion/test_config_page.py</automated>
  </verify>
  <done>
`led_group()` emits a `led-checkbox`-classed label with an unchanged input attribute sequence; `runway_fieldset()` emits exactly one `runway-row` div containing all three cards and nothing else; style.css carries the `.led-checkbox` pair and the `.runway-row` rule and `.runway-card` trades its bottom margin for flex sizing with no other declaration changed; `accent-color` is still declared exactly once file-wide; the structural div-count check is retargeted in place and `companion/test_config_page.py` passes at its still-unchanged `EXPECTED_CHECK_COUNT`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Pin the three fixes with harness checks and run the full suite</name>
  <files>companion/test_config_page.py</files>
  <read_first>
    - `companion/test_config_page.py`'s `EXPECTED_CHECK_COUNT` and the provenance comment block directly above it — read the REAL on-disk value at execution time; this plan deliberately does not name a number.
    - `_runway_fieldset_returns_single_top_level_div()` (as retargeted in Task 2) — the new containment check goes next to it.
    - The `06.6.4.1 Task 3 (D-03, D-04, D-06): cross-file DOM-contract guards` block near the end of Section 1, and specifically `_read_static()` and `_style_css_references_static_save_fallback_attr()` — the third new check reuses that helper and that index-plus-window slicing technique.
    - The `check(name, fn)` helper at the top of `main()` for the return-tuple contract.
  </read_first>
  <action>
Add exactly three checks and bump the count.

**Check A — runway-row containment and ordering.** Place it immediately after the retargeted `_runway_fieldset_returns_single_top_level_div()`. Render `runway_fieldset()` and assert: the row's opening tag appears exactly once; all three runway-card label offsets fall between that opening tag and its matching closing tag; and the escaped `RUNWAY_HELPER_TEXT` offset falls after that closing tag. Reference `config_page.RUNWAY_HELPER_TEXT` through `escape_html()` rather than re-typing the sentence — this file must never become a second place that copy lives.

**Check B — the LED label class and the unchanged input contract.** Place it near the existing LED render assertions. Assert that `led_group(True)` contains the classed label exactly once, that the checkbox's attribute sequence still carries the name and the value drawn from `config_page.LED_CHECKBOX_VALUE` (build the expected substring from that constant, do not re-type the literal) followed by the checked flag, and that `led_group(False)` carries the same classed label with no checked flag. This is what stops a future markup edit from silently reordering the input's attributes and breaking the two live-HTTP LED checks further down the file.

**Check C — cross-file DOM-contract guard.** Place it inside the existing cross-file guard block, alongside `_style_css_references_static_save_fallback_attr()`, and read the stylesheet through that block's own `_read_static()` helper. For each of the three selectors this page module now depends on, locate the selector with `source.index(...)`, slice to the next closing brace, and assert the expected declaration is inside that slice — the same index-plus-window technique the neighbouring guard already uses, never a regex CSS parser. The three pairs to assert: the `.theme-status` rule body carries the card-surface token; a `.theme-status` hover selector exists; the `.runway-row` rule body sets a flex display; and the `.led-checkbox` checkbox rule body clears the global rule's height minimum, without which its 16px sizing is inert. Fail with a message naming which selector or declaration is missing, matching the neighbouring guards' error style.

**Falsifiability pass.** Before finalizing, mutate all three new checks at once so each asserts on a name that does not exist in the source it reads, run the harness, and confirm the output reports exactly those three as FAIL and nothing else. Then restore them. A check that cannot be observed failing is not a check.

**Count bump.** Read the current on-disk `EXPECTED_CHECK_COUNT` and set it to that value plus exactly 3. Do not carry a number over from this plan text. Extend the provenance comment block above it with one new entry in that block's own established format: name this quick task, list the three checks added, and record that Task 2's retarget of the single-top-level-div check was in place with no count change.

**Full suite.** Run `scripts/run-all-tests.sh`. The only harness in its FAILED list must be `server/test_poll_loop.py` — the known, pre-existing, unrelated digest mismatch. If any other harness fails, or if the coverage gate reports a new shortfall, stop and fix it before finishing this task; do not record a green result over a new failure.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 companion/test_config_page.py && test "$(server/.venv/bin/python3 companion/test_config_page.py | tail -1 | sed 's#.*: \([0-9]*\)/\([0-9]*\).*#\1-\2#')" = "$(grep '^EXPECTED_CHECK_COUNT = ' companion/test_config_page.py | sed 's/.*= //' | awk '{print $1"-"$1}')" && scripts/run-all-tests.sh > /tmp/skypane-run-all-tests.log 2>&1; test "$(sed -n '/FAILED harnesses/,$p' /tmp/skypane-run-all-tests.log | grep -c '^    - ')" = 1 && sed -n '/FAILED harnesses/,$p' /tmp/skypane-run-all-tests.log | grep -q 'server/test_poll_loop.py'</automated>
  </verify>
  <done>
`companion/test_config_page.py` passes with every check green, its printed total equals the new `EXPECTED_CHECK_COUNT`, and that value is the real on-disk baseline plus exactly 3. The provenance comment records this task's three additions and Task 2's in-place retarget. Each new check was observed failing under mutation before being restored. `scripts/run-all-tests.sh` lists exactly one failing harness, `server/test_poll_loop.py`.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser -> `GET /settings` | Server-rendered HTML reaches an authenticated operator's browser. Every dynamic value on this page already passes through `escape_html()`. |
| browser -> `POST /settings` | Submitted theme/runway/LED values, validated server-side by `handle_post()` against `device_config`'s own registries. Untouched by this plan. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qif-01 | Tampering | The two new class-name literals added to `runway_fieldset()` / `led_group()` | low | mitigate | Both are constant string literals baked into the format template, never interpolated from user input. No new `%s` slot is introduced and no existing one is moved, so the single `escape_html()` choke point stays exactly where it is. Verified by Task 2's render assertion, which pins the emitted markup shape. |
| T-qif-02 | Elevation of Privilege | `handle_post()` LED validation | low | accept | Out of scope by construction — this plan changes only the `<label>` wrapper, never the `<input>`'s `name`/`value` attributes, and Task 2's verify gate pins that attribute sequence. `handle_post()`'s exact-equality check against `LED_CHECKBOX_VALUE` is untouched and its existing checks still run. |
| T-qif-03 | Denial of Service | Accessibility regression from shrinking the LED checkbox to 16px | medium | mitigate | The 44px activation target is relocated onto the wrapping `<label class="led-checkbox">` (`min-height: 44px`), which a native checkbox label already makes clickable — the same relocation principle `.copy-btn`'s `::before` hit area uses. Task 3's cross-file guard pins the rule, and Task 2 requires the file's 44px floor register comment be updated so the audit stays exhaustive and truthful. |
| T-qif-SC | Tampering | npm/pip/cargo installs | n/a | accept | No package-manager install of any kind. This task edits one stylesheet and two Python files, all stdlib-only, with no dependency change. |
</threat_model>

<verification>
1. `server/.venv/bin/python3 companion/test_config_page.py` — all checks pass; the printed total equals the new `EXPECTED_CHECK_COUNT`, which is the real on-disk baseline plus exactly 3.
2. `scripts/run-all-tests.sh` — exactly one harness in the FAILED list, `server/test_poll_loop.py` (known pre-existing digest mismatch). Coverage gate reports no new shortfall.
3. `git diff --stat` touches only `companion/static/style.css`, `companion/pages/config_page.py`, `companion/test_config_page.py`.
4. `git diff companion/static/style.css` shows: `.theme-status` gained four declarations and a hover/focus-within pair; `.runway-row`, `.led-checkbox` and `.led-checkbox input[type="checkbox"]` are new; `.runway-card` traded `margin-bottom` for two flex declarations. No other rule's declarations changed. `.theme-status__row`, `.theme-swatch`, `.theme-swatch__chip` and every `.runway-card` sibling rule are absent from the diff except as context.
5. `grep -c '^  accent-color: var(--color-accent);' companion/static/style.css` returns 1 — the site-wide native-control tint still lives in exactly one declaration.
6. Manual spot check on the running companion app at `/settings`, both themes: the three groups read as cards matching the Poll section's box; the LED checkbox is a normal small checkbox with an accent tick and a comfortable clickable label; the three runway cards sit in one wrapping row, the selected one still showing its 2px accent border and check glyph; hovering a runway card does not clear its selected border.
</verification>

<success_criteria>
- All three gaps are closed using this stylesheet's own existing tokens and idioms, with no new custom property introduced.
- `.theme-status` and `.page-section` declare an identical box and an identical hover/focus-within reveal.
- The LED checkbox paints at 16px while its label keeps a 44px activation target, and the file's 44px floor register comment reflects that honestly.
- The three runway cards lay out in one wrapping flex row with `.runway-row`'s gap as the single owner of card spacing, and `.runway-card`'s visual treatment is byte-identical to before.
- `EXPECTED_CHECK_COUNT` moved to the real on-disk baseline plus exactly 3, with the retarget recorded as a no-count-change edit.
- `scripts/run-all-tests.sh` shows only the pre-existing `server/test_poll_loop.py` failure.
</success_criteria>

<output>
Create `.planning/quick/260901-qif-fix-3-confirmed-visual-gaps-on-the-compa/260901-qif-SUMMARY.md` when done.
</output>
