---
phase: quick/260904-bbi
plan: 01
type: execute
wave: 1
depends_on: []
branch: claude/sketch-theme-typography-direction   # STAY HERE. Do not create or switch branches.
files_modified:
  - companion/static/style.css
  - companion/test_config_page.py
  - .claude/skills/sketch-findings-skypane/references/control-density.md
  - .claude/skills/sketch-findings-skypane/SKILL.md
autonomous: true
requirements: []          # Decision-point-tracked task, same precedent as every 06.x plan in this
                          # repo (see STATE.md: "Plan has `requirements: []` (Decision-ID-tracked
                          # phase) — requirements.mark-complete not invoked"). Traceability is via
                          # the `decisions` key below, cited inline in every task action.
decisions:
  - DP-1  # Re-key the STRONG treatment (border + wash + check glyph + hover guard) to :has(input:checked)
  - DP-2  # KEEP the server --selected class; it now paints only a QUIET "Current" marker
  - DP-3  # @supports selector(:has(*)) fallback — the server class keeps painting today's strong treatment without :has()
  - DP-4  # Harness CSS-contract checks for both components; EXPECTED_CHECK_COUNT re-derived by RUNNING
  - DP-5  # Supersede control-density.md's "Selected-card treatment" entry in place
  - DP-6  # Real-browser verification, light+dark x 1440px+375px, fresh scratch state dir

must_haves:
  truths:
    - "Clicking an unsaved theme chip moves the strong highlight (2px accent border + 12%-accent body wash + check glyph) to that chip immediately, with no page reload and no JavaScript (DP-1)"
    - "The saved-but-no-longer-chosen chip stops looking selected: it drops to a quiet dashed muted-neutral ring with an English 'Current' tag, and its wash and check glyph are cleared (DP-2)"
    - "Arrow-key navigation inside either radio group moves the strong highlight the same way a click does, because the highlight is keyed to the native :checked state (DP-1)"
    - "Cancel (dirty-state.js's form.reset()) restores the saved card as the sole strong selection and removes every 'Current' marker from the page, with zero JavaScript changes (DP-1)"
    - "Save then reload leaves the newly-saved card as the sole strong selection with no 'Current' marker anywhere (DP-1, DP-2)"
    - "Hovering the newly-checked card can never clear its accent border — D-03a's guarantee, transferred from the server class to live state (DP-1)"
    - "The identical behaviour holds for the runway picker, not only the theme chips (DP-1, DP-2)"
    - "In a browser without :has() support the server-rendered --selected class alone still paints today's full strong treatment; nothing regresses to unstyled (DP-3)"
  artifacts:
    - "companion/static/style.css — one @supports selector(:has(*)) block covering BOTH .theme-chip and .runway-card, placed immediately after the .theme-chip group"
    - "companion/test_config_page.py — two new CSS-contract checks (strong-rules-keyed-to-:checked; --selected-degrades-to-quiet-marker) with EXPECTED_CHECK_COUNT re-derived by running the harness"
    - ".claude/skills/sketch-findings-skypane/references/control-density.md — 'Selected-card treatment' entry superseded in place with the live-state re-key, the quiet-marker role of the server class, and the fallback story"
  key_links:
    - "The <input type=\"radio\"> is a DESCENDANT of <label class=\"theme-chip|runway-card\"> (config_page.py:277, :388) — this is what makes :has(input:checked) resolvable; if that nesting ever changes, every rule in the @supports block silently stops matching"
    - "The saved radio is server-rendered with the `checked` attribute (config_page.py:267, :372) — this is what makes :has() correct on FIRST paint, not only after a click"
    - "dirty-state.js:177 Cancel = form.reset(), which reverts the DOM `checked` property to the HTML `checked` attribute — this is why Cancel needs zero JS changes to restore the saved highlight"
    - "The four literal-pinned selectors in test_config_page.py (see <harness_hazards>) must survive byte-for-byte; the new selectors are constructed so none of them is a substring collision"
---

<objective>
Fix the Settings page defect the developer found at the 06.6.4.1.1-06 checkpoint follow-up: the
selected-state highlight follows the SAVED config, not the user's LIVE choice. Clicking "Blue"
while "White" is saved leaves White painted as selected (border + 12% wash + check glyph) and
Blue painted as unselected — only the dirty bar changes. Same defect, pre-existing and less
noticeable, on the runway picker.

Root cause is already diagnosed and is NOT to be re-derived: `companion/pages/config_page.py:269`
and `:374` compute the `--selected` modifier SERVER-SIDE from the saved config and paint it once;
every selected-state CSS rule keys off that class; `companion/static/dirty-state.js` never touches
it (it only snapshots/compares form values and shows the bar).

Purpose: make the strong "this is your selection" treatment follow live `:checked` state via pure
CSS, and demote the server class to an honest, quiet "this is what is saved" marker — so the wash
06.6.4.1.1-06 added (the right idiom keyed to the wrong signal) stops amplifying a stale highlight.

Output: one `@supports selector(:has(*))` block in `style.css`, two new harness CSS-contract
checks, a superseded design-system entry, and recorded real-browser measurements.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./.claude/CLAUDE.md
@.claude/skills/sketch-findings-skypane/SKILL.md
@.claude/skills/sketch-findings-skypane/references/control-density.md
@.planning/phases/06.6.4.1.1-settings-theme-picker-and-typography-spacing-direction-pass/06.6.4.1.1-06-SUMMARY.md
</context>

<branch_discipline>
This work runs on the CURRENT branch `claude/sketch-theme-typography-direction`, where phase
06.6.4.1.1 is committed and unmerged, and where `.theme-chip` exists at all. Do NOT create a
branch, do NOT branch off `main`, do NOT use worktree isolation (see the
`project_skypane_worktree_isolation_base_mismatch` memory — isolation forks from `main` in this
repo and would produce a tree with no `.theme-chip`). Run `git rev-parse --abbrev-ref HEAD` before
the first edit and confirm it prints `claude/sketch-theme-typography-direction`; stop if it does not.
</branch_discipline>

<already_verified_facts>
Confirmed by direct read during planning — do not spend context re-confirming:

- `config_page.py:277` — `<input type="radio" name="theme" ... class="visually-hidden"%s>` is the
  FIRST child of `<label class="%s">` where `%s` is `theme-chip` / `theme-chip theme-chip--selected`.
  `:has(input:checked)` therefore resolves against the label.
- `config_page.py:388` — same shape for `<label class="runway-card...">` and
  `name="tracked_runway"`.
- `config_page.py:267` / `:372` — `checked = " checked" if selected else ""`, so the SAVED radio
  carries the `checked` HTML attribute at first paint. `:has()` is correct on initial render, not
  only after interaction.
- `dirty-state.js` contains exactly two relevant lines: `:71` `if (el.checked)` (snapshotting) and
  `:177` `form.reset()` (Cancel). Zero `classList` use, zero `--selected` references. It needs no
  hook for a `:checked`-driven approach and must receive a ZERO diff.
- `style.css:1673-1677` — `.theme-chip`'s sibling guard precedent
  `.runway-card:not(.runway-card--selected):hover, ...:focus-within { border-color: transparent;
  box-shadow: var(--shadow-card-hover); }` (D-03a).
- `style.css:1705-1708` — `.runway-card--selected { border: 2px solid var(--color-accent);
  background: color-mix(in srgb, var(--color-accent) 12%, transparent); }`
- `style.css:1781-1785` — `.theme-chip:not(.theme-chip--selected):hover, ...:focus-within` guard.
- `style.css:1790-1792` — `.theme-chip--selected { border: 2px solid var(--color-accent); }`
  (border only, no background — pinned that way by the harness).
- `style.css:1807-1809` — `.theme-chip--selected .theme-chip__body { background: color-mix(...12%...); }`
- `style.css:1727-1737` / `:1859-1869` — `.runway-card__check` / `.theme-chip__check` are
  `display: none` by default, flipped to `inline-flex` by the `--selected` descendant rule.
- `style.css:1745` — the existing comment claims the mechanism is "a server-computed --selected
  modifier (never a client-side `:has()` trick)". That sentence is PRIOR REASONING ON EXACTLY THIS
  QUESTION and is now falsified by the defect. It must be rewritten in place, not left standing.
  `config_page.py:320` carries the same claim in `runway_fieldset()`'s docstring — see the
  <scope_guard> for how to handle that one without touching the file.
- `style.css` already contains `color-mix(in srgb, var(--color-text) 70%, transparent)` **16 times**
  — this is the file's established muted-text strength. `55%` appears once. No new percentage is
  needed or permitted (the skill's "What to Avoid" forbids a second muted strength).
- `style.css` has no text-bearing `content:` property yet (only `content: ""` at `:1100`, `:1600`).
- `style.css:1387-1389`, `:4138-4139`, `:4148-4149` — the WR-02 fallback idiom: a plain declaration
  immediately followed by the enhanced `color-mix()` one, so a non-supporting browser keeps the
  first. This is the precedent DP-3's `@supports` gating mirrors at the selector level.
- `scripts/run-all-tests.sh` exists; `companion/app.py` accepts `--port` and `--state-dir`.
- The cached Playwright Chromium is at `~/Library/Caches/ms-playwright/chromium-1228`.
</already_verified_facts>

<harness_hazards>
`companion/test_config_page.py` pins CSS selectors by EXACT LITERAL via `source.index('...{')` and
pins server-rendered markup by EXACT COUNT. Extending or renaming a pinned selector turns a passing
check into a failure (and, in the `.index()` cases, can throw). This is a recurring hazard in this
repo — three prior plans in this phase alone recorded self-caught collisions.

**Rule for every hazard below: RETARGET, NEVER DELETE.** If a check needs to change, invert or
extend its contract in place and keep its name/description meaningful. Do not delete a check to
make the suite green.

| # | Location | What is pinned | Why it survives this plan |
|---|----------|----------------|---------------------------|
| H1 | `test_config_page.py:1702-1707` | `source.index(".theme-chip--selected {")`, window must contain `var(--color-accent)` | The rule is left BYTE-FOR-BYTE unchanged (DP-3 fallback). `.theme-chip--selected:not(...)` does not contain the literal `.theme-chip--selected {` (colon, not space, follows) — no substring collision, and `.index()` still finds the original rule first. |
| H2 | `test_config_page.py:1829-1839` | `source.index(".runway-card--selected {")`, then a **1600-char window** that must contain `border: 2px solid var(--color-accent);` AND the 12% wash | Rule left unchanged; nothing is inserted between the selector and its declarations. |
| H3 | `test_config_page.py:1847-1855` | `.theme-chip--selected {` rule body (up to its next `}`) must NOT contain `background:` | Do NOT add any background to `.theme-chip--selected` itself. The chip's wash stays scoped to `.theme-chip__body` in both the fallback and the `:has()` forms. |
| H4 | `test_config_page.py:1857-1865` | `.theme-chip--selected .theme-chip__body {` + 200-char window must contain the wash | Rule left unchanged. `.theme-chip--selected:not(:has(input:checked)) .theme-chip__body {` does not contain that literal. |
| H5 | `test_config_page.py:1686-1714` | `.theme-chip-grid {`, `.theme-chip {`, `.theme-chip--selected {`, `.theme-chip__preview {` + windows | `.theme-chip:has(...)` does not contain `.theme-chip {`. All four base rules untouched. |
| H6 | `test_config_page.py:649-650`, `:671-674`, `:901-906` | SERVER-SIDE counts: `'theme-chip theme-chip--selected' in rendered`; exactly 3 `<label class="runway-card`; exactly ONE `runway-card--selected`; exactly ONE `theme-chip--selected` | `config_page.py` gets a ZERO diff, so all of these stay valid untouched. **Do not touch these assertions.** |
| H7 | `test_config_page.py:1769-1783` | exactly `len(THEME_IDS)` occurrences of `<span class="theme-chip__check">` | Markup unchanged; the check glyph stays present on every chip and is shown/hidden purely in CSS. |
| H8 | `test_config_page.py:123` and `:142` | `EXPECTED_CHECK_COUNT` is assigned TWICE; the second (`:142`, value 70) wins | Edit the assignment at `:142`. Re-derive the new value by RUNNING the harness and reading the reported total — never by arithmetic. |

Additional collision class specific to this plan: several new selectors and property values must
be named inside CSS comments. Prior plans in this phase tripped their own greps this way. Before
committing, re-run the harness and the raw greps in each task's acceptance criteria; if a comment's
prose collides, reword the COMMENT (never weaken the check) — that is the established fix pattern
here, recorded in the 06.6.4.1.1-02/-03/-05 SUMMARYs.
</harness_hazards>

<current_tag_markup_decision>
DP-2 asks for a decision between a CSS `::after` with `content: "Current"` (zero Python) and a real
`<span>` (touches `config_page.py` and H6/H7's exact-count assertions).

**Decision: CSS `::after`. `config_page.py` gets a zero diff.**

Reasoning, to be restated in the CSS comment:
1. The authoritative selection state for assistive technology is the native radio's `checked`
   property inside a real radio group — that is announced natively and is exactly the state the
   marker is derived from. The tag adds no information AT does not already have.
2. The pending-vs-saved distinction is already carried in real DOM text by the dirty bar
   ("Theme changed · Save settings · Cancel"), which is announced. The tag is a supplementary
   VISUAL cue for a sighted user comparing 16 dense chips against the saved one.
3. A real `<span>` would inject a redundant announcement into exactly 1 of 16 chips and force
   retargeting of H6/H7's exact-count assertions for zero accessibility gain.
4. Modern engines do expose `content` text in the accessibility tree, so this is not invisible to
   AT either — it simply is not relied upon.

Accessibility therefore does not require a DOM element here, which is the bar DP-2 set. If a future
change makes the tag the ONLY carrier of the saved-vs-live distinction (e.g. the dirty bar is
removed), revisit this.
</current_tag_markup_decision>

<css_design>
One `@supports selector(:has(*))` block, covering BOTH components, placed immediately after the
`.theme-chip` group ends (after the touch-target comment at `style.css:1871-1874`, before
`.led-checkbox`). Placement is for READABILITY, not cascade — state that in the comment, because
this file has genuine source-order-dependent rules elsewhere and a future reader must not assume
this is one of them.

**Specificity arithmetic (verified during planning — reproduce it in the comment, do not re-derive):**

- `:has(X)` and `:not(X)` each take the specificity of their most specific argument.
- `.theme-chip--selected` = (0,1,0) — the fallback.
- `.theme-chip:has(input:checked)` = (0,1,0) + (0,1,1) = **(0,2,1)** → beats the fallback.
- `.theme-chip--selected:not(:has(input:checked))` = (0,1,0) + (0,1,1) = **(0,2,1)** → beats the
  fallback, and can never match the same element as the rule above (one requires a checked
  descendant, the other forbids one) — so the equal specificity is not a conflict.
- The existing hover guard `.theme-chip:not(.theme-chip--selected):hover` = **(0,3,0)**, which
  BEATS (0,2,1). It matches the newly-clicked chip (which lacks `--selected`) and would clear its
  accent border. This is the trap. The fix is a positive restore rule at
  `.theme-chip:has(input:checked):hover` = (0,2,1) + (0,1,0) = **(0,3,1)**, which wins.
  Do NOT instead rewrite the base guard's `:not(.theme-chip--selected)` to `:not(:has(...))` — an
  unsupported `:has()` invalidates the whole selector list and would drop the hover reveal entirely
  in non-supporting browsers, violating DP-3.

**Fallback story (DP-3), to be stated in the comment:** every rule that keys off live state lives
inside the feature query. A browser without `:has()` evaluates `@supports selector(:has(*))` as
false, skips the whole block, and is left with exactly today's shipped behaviour — the server
`--selected` class painting the full strong treatment. Nothing degrades to unstyled. This mirrors
the file's own WR-02 idiom (plain declaration first, enhanced form second) one level up, at the
selector rather than the value.

**Colour register (skill rule: no new muted strength, no new wash percentage):** both the dashed
ring and the tag text use `color-mix(in srgb, var(--color-text) 70%, transparent)` — the file's
established muted strength, already present 16 times. The tag reuses the app's unified label voice
verbatim: 12px, `var(--weight-semibold)`, `text-transform: uppercase`, `letter-spacing: 0.06em`,
70% muted. No accent anywhere in the quiet-marker rules — that is the whole point of "discret".

**Ring width is 2px dashed, not 1px:** with the global `border-box` reset, keeping 2px means the
saved card's content box is identical whether or not it is still the live choice, so toggling
between the strong and quiet states causes zero content shift. The difference reads as colour and
dash pattern, never as geometry.

**Marker placement differs per component, deliberately, for the same reason the wash already does:**
- `.runway-card` — top-right, the check glyph's own vacated slot. The card's content is a text
  number plus an optional airport-diagram image below it; the top-right corner is free.
- `.theme-chip` — bottom-right (over the body's own flat surface, to the right of the two 12px
  swatch dots). NOT top-right, because on this component top-right sits over
  `.theme-chip__preview`, the rendered panel image — the identical constraint that made the wash
  body-scoped at 06.6.4.1.1-06. Both components are `position: relative` already.
</css_design>

<scope_guard>
Files this plan may touch: `companion/static/style.css`, `companion/test_config_page.py`,
`.claude/skills/sketch-findings-skypane/references/control-density.md`, and
`.claude/skills/sketch-findings-skypane/SKILL.md` (one-line pointer refresh only).

**Zero diff required, verified by `git diff --quiet` before each commit:**
`companion/pages/config_page.py`, `companion/static/dirty-state.js`, `companion/layout.py`,
`companion/app.py`, every other page module, every other harness, everything under `server/`.

Note on `config_page.py:320` — `runway_fieldset()`'s docstring also says the modifier is computed
server-side "never a client-side `:has()` CSS trick". That sentence remains literally TRUE of the
Python (the class is still server-computed, and still marks the saved value), so it does not
require an edit. Do not touch it. The now-falsified claim is `style.css:1745`'s, which asserts the
mechanism DRIVES the border — that one is in scope and must be rewritten.
</scope_guard>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Re-key both selectable-card components to live :checked state, with a server-class quiet marker and a no-:has() fallback</name>
  <files>companion/static/style.css, companion/test_config_page.py</files>
  <read_first>
    - `companion/static/style.css:1-70` (header accent-reservation list, colour-separation contract)
    - `companion/static/style.css:1636-1737` (the `.runway-card` group in full)
    - `companion/static/style.css:1739-1874` (the `.theme-chip` group in full, including `:1745`'s
      now-falsified `:has()` claim)
    - `companion/static/style.css:1380-1392` and `:4126-4150` (the WR-02 fallback idiom precedent)
    - `companion/test_config_page.py:119-145` (both `EXPECTED_CHECK_COUNT` assignments; `:142` wins)
    - `companion/test_config_page.py:1608-1721` (`_read_static`, the `.index()`-plus-window
      technique, H1/H5)
    - `companion/test_config_page.py:1817-1871` (the 06.6.4.1.1-06 wash check — H2/H3/H4; this is
      the check to EXTEND alongside, not to retarget)
    - `companion/pages/config_page.py:264-298` and `:369-408` (READ ONLY — confirm the radio nesting
      and the `checked` attribute; this file gets a zero diff)
  </read_first>
  <behavior>
    Contract this task must make true in `companion/static/style.css`, expressed as the checks
    Task 1 writes BEFORE the CSS (RED), then satisfies (GREEN):

    - Test 1 (strong treatment keyed to live state, DP-1): the file declares
      `@supports selector(:has(*)) {`, and inside it — proven positionally, by index, not merely by
      presence — `.theme-chip:has(input:checked)` carrying `border: 2px solid var(--color-accent);`,
      `.theme-chip:has(input:checked) .theme-chip__body` carrying
      `background: color-mix(in srgb, var(--color-accent) 12%, transparent);`, and
      `.theme-chip:has(input:checked) .theme-chip__check` carrying `display: inline-flex;`.
    - Test 2 (same for the runway picker, DP-1): `.runway-card:has(input:checked)` carrying BOTH the
      2px accent border and the 12% wash (whole card, no body wrapper exists), and
      `.runway-card:has(input:checked) .runway-card__check` carrying `display: inline-flex;`.
    - Test 3 (D-03a transferred to live state, DP-1): a `:hover, :focus-within` restore rule exists
      for each component keyed to `:has(input:checked)`, and its body declares
      `border-color: var(--color-accent);` and `box-shadow: none;`.
    - Test 4 (server class demoted to a quiet marker, DP-2): for each component, a
      `--selected:not(:has(input:checked))` rule whose body contains `dashed` and
      `color-mix(in srgb, var(--color-text) 70%, transparent)` and does NOT contain
      `var(--color-accent)`; companion rules clearing that state's wash and hiding its check glyph.
    - Test 5 ("Current" tag, English copy, DP-2): a `::after` rule on each component's quiet-marker
      selector whose body contains `content: "Current";`; the file contains exactly two
      `content: "Current";` occurrences; the file contains zero occurrences of the French word for
      "current" that DP-2 forbids. <!-- planner-discipline-allow: Actuel -->
    - Test 6 (fallback intact, DP-3): all four pre-existing server-class rules still exist verbatim
      — `.theme-chip--selected {`, `.theme-chip--selected .theme-chip__body {`,
      `.runway-card--selected {`, and each component's `--selected ... __check` display rule — and
      each of the four `:has()`-keyed strong selectors appears at a source index GREATER than the
      `@supports selector(:has(*)) {` opening index (i.e. is genuinely inside the feature query).
    - Test 7 (register discipline, DP-2): the literal
      `color-mix(in srgb, var(--color-text) 70%, transparent)` occurs at least 17 times in the file
      (16 pre-existing plus the new marker rules), proving reuse of the established muted strength
      rather than invention of a new one.
  </behavior>
  <action>
    Follow the file's own RED/GREEN discipline used by 06.6.4.1.1-04: write the two new harness
    checks FIRST, run the harness against the UNMODIFIED `style.css`, and confirm they genuinely
    fail (record the RED count in the SUMMARY). Then write the CSS and confirm GREEN. Two commits:
    `test(260904-bbi): ...` then `fix(260904-bbi): ...`.

    Read `<harness_hazards>`, `<current_tag_markup_decision>` and `<css_design>` above before
    writing anything — the specificity arithmetic, the placement, the colour register and the
    marker-slot asymmetry are all decided and must not be re-litigated.

    CSS edits, all in `companion/static/style.css`:

    (a) Rewrite the falsified sentence at `:1745`. The existing `.theme-chip` group comment states
    the mechanism is "a server-computed --selected modifier (never a client-side :has() trick)
    driving a real 2px accent border". That is now wrong and is exactly the reasoning this task
    reverses. Rewrite it in place, preserving the SUPERSEDED convention this repo uses: record that
    the server modifier still marks the SAVED value and is still the no-`:has()` fallback, but that
    driving the strong treatment from it was the defect — the saved highlight did not move when the
    user clicked another chip, and 06.6.4.1.1-06's wash amplified the stale one. Do the same for
    `.runway-card`'s group comment, which shares the mechanism. Leave
    `companion/pages/config_page.py:320`'s docstring alone (see `<scope_guard>` — that sentence is
    still literally true of the Python).

    (b) Add ONE `@supports selector(:has(*)) { ... }` block immediately after the `.theme-chip`
    group's closing touch-target comment (`:1871-1874`) and before `.led-checkbox`. Inside it, in
    this order, with the block's own leading comment carrying (i) the defect diagnosis in one
    sentence, (ii) the specificity arithmetic from `<css_design>` including WHY the base hover guard
    is left alone and answered with a positive restore rule instead, (iii) the DP-3 fallback story
    and its relationship to the file's WR-02 idiom, (iv) the note that placement is for readability,
    not cascade:

    - `.theme-chip:has(input:checked)` → `border: 2px solid var(--color-accent);`
    - `.theme-chip:has(input:checked) .theme-chip__body` → the 12% accent wash literal
    - `.theme-chip:has(input:checked) .theme-chip__check` → `display: inline-flex;`
    - `.theme-chip:has(input:checked):hover, .theme-chip:has(input:checked):focus-within` →
      `border-color: var(--color-accent); box-shadow: none;` (D-03a transferred: the base guard at
      `:1781` is `:not(.theme-chip--selected)`-scoped, which is now the wrong signal and still
      matches the newly-clicked chip)
    - `.theme-chip--selected:not(:has(input:checked))` → `border: 2px dashed
      color-mix(in srgb, var(--color-text) 70%, transparent);`
    - `.theme-chip--selected:not(:has(input:checked)) .theme-chip__body` → `background: transparent;`
    - `.theme-chip--selected:not(:has(input:checked)) .theme-chip__check` → `display: none;`
    - `.theme-chip--selected:not(:has(input:checked))::after` → `content: "Current";` plus
      `position: absolute; bottom: var(--space-sm); right: var(--space-sm);` and the unified label
      voice (12px, `var(--weight-semibold)`, `text-transform: uppercase`, `letter-spacing: 0.06em`,
      `color: color-mix(in srgb, var(--color-text) 70%, transparent);`). Comment WHY bottom-right
      here and top-right on the runway card — same preview-band constraint that made the wash
      body-scoped at 06.6.4.1.1-06. Comment the `<current_tag_markup_decision>` reasoning for why
      this is a pseudo-element and not a `<span>`.
    - `.runway-card:has(input:checked)` → `border: 2px solid var(--color-accent);` plus the 12%
      accent wash (whole card — no body wrapper exists on this component)
    - `.runway-card:has(input:checked) .runway-card__check` → `display: inline-flex;`
    - `.runway-card:has(input:checked):hover, .runway-card:has(input:checked):focus-within` →
      `border-color: var(--color-accent); box-shadow: none;`
    - `.runway-card--selected:not(:has(input:checked))` → the same 2px dashed 70%-muted ring plus
      `background: transparent;`
    - `.runway-card--selected:not(:has(input:checked)) .runway-card__check` → `display: none;`
    - `.runway-card--selected:not(:has(input:checked))::after` → `content: "Current";` plus
      `position: absolute; top: var(--space-sm); right: var(--space-sm);` and the same label voice

    (c) Change NOTHING outside that block except the two rewritten group comments in (a) and the
    header-comment amendment in (d). In particular: do not touch `.theme-chip--selected`,
    `.theme-chip--selected .theme-chip__body`, `.runway-card--selected`, either base hover guard,
    or either base `__check` rule — H1 through H5 depend on all of them surviving byte-for-byte.

    (d) Extend the file's header accent-reservation list (`:10-34`), which is kept exhaustive on
    purpose. The accent is now consumed by a LIVE-STATE selector rather than only the server class
    on those same two components — record that as a re-keying of an already-listed use, not a new
    component, and note that the new quiet marker deliberately uses NO accent (a muted-text mix and
    a dashed edge), so it adds nothing to the list.

    Harness edits, in `companion/test_config_page.py`, appended immediately after
    `_selected_runway_card_and_theme_chip_carry_a_background_wash` (`:1817-1871`) so the three
    selected-state checks read as one group:

    - `_strong_selected_treatment_is_keyed_to_the_live_checked_radio()` — Tests 1, 2, 3, 6 above.
      Use the file's own established `source.index(selector)` plus bounded-window technique, and for
      Test 6 compare indices against `source.index("@supports selector(:has(*)) {")`.
    - `_saved_but_unchecked_card_degrades_to_a_quiet_current_marker()` — Tests 4, 5, 7 above.
    - Bump `EXPECTED_CHECK_COUNT` at `:142`. **Re-derive by RUNNING the harness and reading the
      reported total. Never by arithmetic.** Extend the existing running commentary at `:123-141`
      with a one-line entry in the same voice.
    - Do NOT weaken, retarget or delete the existing wash check or any H1-H7 assertion. The wash
      check keeps proving the FALLBACK still paints; the two new checks prove the live-state layer.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 companion/test_config_page.py; test $? -eq 0</automated>
  </verify>
  <acceptance_criteria>
    Independent of the harness — every one of these is a raw assertion against the file, so a
    gutted or deleted harness check still fails this plan:

    1. `grep -c '@supports selector(:has(\*)) {' companion/static/style.css` returns `1`.
    2. All eight live-state strong selectors exist:
       `grep -c ':has(input:checked)' companion/static/style.css` returns at least `14`.
    3. Both quiet-marker rings exist and are accent-free. Run:
       `python3 -c "import re,sys; s=open('companion/static/style.css').read();
       bodies=[s[s.index(k)+len(k):s.index('}',s.index(k))] for k in
       ('.theme-chip--selected:not(:has(input:checked)) {','.runway-card--selected:not(:has(input:checked)) {')];
       sys.exit(0 if all('dashed' in b and 'color-mix(in srgb, var(--color-text) 70%, transparent)' in b
       and 'var(--color-accent)' not in b for b in bodies) else 1)"` and require exit 0.
    4. `grep -c 'content: \"Current\";' companion/static/style.css` returns exactly `2`.
    5. The French copy DP-2 forbids appears nowhere:
       `grep -ci 'actuel' companion/static/style.css` returns `0`.
       <!-- planner-discipline-allow: actuel -->
    6. Register discipline: `grep -c 'color-mix(in srgb, var(--color-text) 70%, transparent)'
       companion/static/style.css` returns at least `17` (16 pre-existing + the marker rules), and
       `grep -o 'color-mix(in srgb, var(--color-text) [0-9.]*%' companion/static/style.css | sort -u`
       lists ONLY strengths that already existed before this change (no new percentage).
    7. Fallback intact — all four pinned literals survive:
       `grep -c '^\.theme-chip--selected {' companion/static/style.css` returns `1`;
       `grep -c '^\.theme-chip--selected \.theme-chip__body {' companion/static/style.css` returns `1`;
       `grep -c '^\.runway-card--selected {' companion/static/style.css` returns `1`;
       and `git diff -- companion/static/style.css | grep -c '^-.*--selected {'` returns `0`
       (no pinned selector line was removed).
    8. Zero diff outside scope: `git diff --quiet companion/pages/config_page.py
       companion/static/dirty-state.js companion/layout.py companion/app.py` exits 0, and
       `git diff --stat` across this task's two commits lists exactly `companion/static/style.css`
       and `companion/test_config_page.py`.
    9. `server/.venv/bin/python3 companion/test_config_page.py` exits 0 at the re-derived count, and
       the RED run (checks written, CSS not yet written) was recorded as genuinely failing.
    10. `server/.venv/bin/ruff check .` is clean.
  </acceptance_criteria>
  <done>
    `style.css` carries one `@supports selector(:has(*))` block re-keying the strong treatment of
    both `.theme-chip` and `.runway-card` to live `:checked` state, demoting each server
    `--selected` class to an accent-free dashed 70%-muted ring plus an English "Current"
    pseudo-element tag, with every pre-existing server-class rule left byte-for-byte intact as the
    no-`:has()` fallback. `config_page.py` and `dirty-state.js` have a zero diff. Two new harness
    checks pass; the existing wash check still passes unmodified; `EXPECTED_CHECK_COUNT` was
    re-derived by running the harness.
  </done>
</task>

<task type="auto">
  <name>Task 2: Prove it in a real browser — light+dark x 1440px+375px, both pickers, click / arrow keys / Cancel / Save+reload</name>
  <files>(no repo files modified — measurements are recorded in the SUMMARY; the driver script lives in the scratch dir)</files>
  <read_first>
    - `.planning/phases/06.6.4.1.1-settings-theme-picker-and-typography-spacing-direction-pass/06.6.4.1.1-06-SUMMARY.md`
      lines ~30-60 and ~135-200 — the established fallback recipe for this environment, including
      why no MCP browser tool is reachable from a subagent and how login was performed
    - `companion/app.py` `main()` / the `argparse` block (`:1434-1460`) — `--port`, `--state-dir`
    - The `feedback_claude_browser_hidden_pane_screenshots` memory — hidden panes freeze
      transitions and blank scrolled captures; use a tall viewport
  </read_first>
  <action>
    Real-browser verification per DP-6. No MCP browser tool is reachable from a subagent here — use
    the established fallback recorded in 06.6.4.1.1-06-SUMMARY.md: the cached Playwright Chromium at
    `~/Library/Caches/ms-playwright/chromium-1228`, launched with the LEGACY `--headless` flag.
    **Never `--headless=new`** — that reproduced a hang in this environment. Drive it over raw CDP.

    Setup:
    - Start a companion instance against a FRESH scratch state dir under the session scratch
      directory (never a production snapshot, never the repo), on a free port.
    - Authenticate with a real `POST /login`, then install the resulting session cookie via CDP
      `Network.setCookie` (per prior SUMMARYs).
    - Write the driver as a script in the scratch directory. It is a verification artifact, not a
      repo file — do not commit it.

    Run the full matrix: {light, dark} x {1440px, 375px} x {theme picker, runway picker} = 8 runs.
    Use a tall viewport so nothing is captured mid-scroll. In each run, record `getComputedStyle`
    readings (not screenshots alone) at each of these six states:

    S1. Initial load. The saved card: `borderStyle` is `solid`, `borderColor` resolves to the
        accent, its wash surface is the 12% accent mix, its check glyph is `inline-flex`, and
        `getComputedStyle(el, '::after').content` is `none`. Every other card: 1px hairline, no
        wash, check `none`, `::after` `none`.
    S2. Click a DIFFERENT card. The clicked card takes the full strong treatment (solid accent 2px
        border, wash, check shown). The saved card now reads: `borderStyle` `dashed`, `borderColor`
        is the 70% muted-text mix and is NOT the accent, wash surface transparent, check `none`,
        `::after` content is `"Current"`. Count of elements on the page whose `::after` content is
        `"Current"` is exactly 1.
    S3. Hover the newly-clicked card (CDP `Input.dispatchMouseEvent` move over its centre). Its
        `borderColor` STILL resolves to the accent and `boxShadow` is `none` — the D-03a transfer.
        This is the specific regression the base `:not(--selected)` guard would otherwise cause.
    S4. Focus the checked radio and press ArrowDown (and ArrowRight) via `Input.dispatchKeyEvent`.
        The strong treatment moves to the newly-checked card; the marker stays on the saved card.
    S5. Click the dirty bar's Cancel. The saved card is the SOLE strong selection again, and the
        count of `"Current"` `::after` elements on the page is 0.
    S6. Click Save, wait for the redirect, reload. The newly-saved card is the sole strong
        selection; `"Current"` count is 0; the server-rendered `--selected` class is now on that
        same card (confirming the fallback and the live state agree at rest).

    Additionally, at 375px and at 1440px, assert NO overlap between the `"Current"` tag's rendered
    box and the card's own content: for `.runway-card`, the tag's bounding rect must not intersect
    `.runway-card__number`'s rect; for `.theme-chip`, it must not intersect `.theme-chip__swatches`'
    rect and must not extend over `.theme-chip__preview`. If an overlap IS measured, record the
    measurement, adjust the tag's inset or slot in `style.css` within this task, and re-run — do not
    ship a measured collision and do not silently reposition without recording the original numbers.

    Capture one screenshot per {theme, width} at S2 (the state the whole fix exists for) as visual
    evidence, and record every computed-style reading as a measurement table in the SUMMARY.

    Stop the browser and the companion instance cleanly when done.
  </action>
  <verify>
    <automated>Driver script in the scratch dir exits 0 with every S1-S6 assertion and both overlap assertions passing across all 8 runs; its stdout measurement table is pasted into the SUMMARY</automated>
  </verify>
  <acceptance_criteria>
    1. All 8 runs ({light,dark} x {1440,375} x {theme,runway}) completed against a FRESH scratch
       state dir — the state dir path is recorded and is outside the repo and outside any production
       snapshot.
    2. S2 is proven by computed style, not by eye: the clicked card's `borderColor` equals the
       theme's accent and the saved card's does not, in all four theme/width combinations.
    3. S3 passes in all four combinations — this is the assertion that would fail if the base hover
       guard had been left as the only guard.
    4. S5 yields exactly 0 `"Current"` markers and exactly 1 strong selection, in all four
       combinations, for both pickers.
    5. S6 yields exactly 0 `"Current"` markers and the server class and live state agree.
    6. Both overlap assertions pass at 375px AND 1440px; if any adjustment was made, the original
       measured collision and the fix are both recorded.
    7. Chromium was launched with legacy `--headless` — the SUMMARY states this explicitly, and no
       `--headless=new` appears anywhere in the driver.
    8. `git status --porcelain` shows no new untracked file inside the repo (the driver lives in the
       scratch dir).
  </acceptance_criteria>
  <done>
    A recorded measurement table in the SUMMARY proves, from real `getComputedStyle` readings in a
    real browser across light+dark and 1440px+375px, that the strong highlight follows clicks and
    arrow keys, that the saved-but-unchosen card degrades to the quiet "Current" marker, that
    hovering the newly-chosen card cannot clear its accent border, and that Cancel and Save+reload
    both return the page to exactly one strong selection with no marker — on both the theme picker
    and the runway picker.
  </done>
</task>

<task type="auto">
  <name>Task 3: Supersede the design system's "Selected-card treatment" entry in place</name>
  <files>.claude/skills/sketch-findings-skypane/references/control-density.md, .claude/skills/sketch-findings-skypane/SKILL.md</files>
  <read_first>
    - `.claude/skills/sketch-findings-skypane/references/control-density.md:27` (the
      "Selected-card treatment" entry written by 06.6.4.1.1-06 — the one to supersede),
      `:74-84` (the CSS Patterns snippet showing the `--selected`-keyed rules),
      `:86-96` (the "What to Avoid" list and the Origin line)
    - `.claude/skills/sketch-findings-skypane/SKILL.md:26` (accent-reservation pointer), `:47-49`
      (the card contract and the two selected-state bullets), `:107` (the Folded-In Work entry for
      06.6.4.1.1 ending on the background-wash fix)
    - This plan's `<css_design>` and `<current_tag_markup_decision>` sections
    - Task 2's recorded measurements
  </read_first>
  <action>
    Update the design system of record to describe what now ships (DP-5), using this project's
    SUPERSEDED-marker convention: correct entries IN PLACE, keep the prior reasoning legible and
    marked, never delete history.

    In `references/control-density.md`:
    - Rewrite the "Selected-card treatment" entry (`:27`). It currently states the border + wash +
      check glyph are keyed off `--selected` and that each component's hover rule is
      `:not(...--selected)`-scoped. Mark the `--selected`-keyed strong treatment SUPERSEDED and
      state the current contract: the strong treatment is keyed to live `:has(input:checked)`; the
      server `--selected` class still truthfully marks the SAVED value and now drives only a quiet,
      accent-free dashed 70%-muted ring plus an English "Current" pseudo-element tag when the saved
      value is no longer the live choice; at rest (saved == checked) the strong rule wins and no tag
      shows. Record WHY: the border+wash 06.6.4.1.1-06 added was the right idiom keyed to the wrong
      signal, so clicking a chip left the stale saved highlight looking MORE selected than the live
      choice — the wash amplified the defect rather than causing it.
    - Record the fallback story: everything live-state lives inside `@supports selector(:has(*))`,
      so a browser without `:has()` falls back to exactly the previous shipped behaviour. Name this
      as the selector-level analogue of the file's WR-02 value-level fallback idiom.
    - Record the D-03a transfer and WHY it is a positive restore rule rather than a re-scoped guard
      (rewriting the base guard's `:not()` to use `:has()` would invalidate the whole selector list
      in non-supporting browsers). Include the specificity arithmetic — this is the part a future
      reader is most likely to get wrong.
    - Record the marker-slot asymmetry (chip bottom-right, runway top-right) and its one reason:
      the chip's rendered preview band, the same constraint that already scopes the chip's wash to
      `.theme-chip__body`.
    - Record the pseudo-element-not-`<span>` decision and its four-point justification, so a future
      reader does not "fix" it into a DOM element and break the harness's exact-count assertions.
    - Update the CSS Patterns snippet (`:74-84`) to show both layers: the unchanged `--selected`
      fallback rules AND the `@supports`-gated live-state rules.
    - Update "What to Avoid" (`:86-96`): the existing bullet forbidding a border-only selected-card
      treatment stays; ADD bullets forbidding (a) keying a selected-state treatment off a
      server-rendered class alone on any form control that can change client-side, (b) rewriting
      either base hover guard's `:not()` to use `:has()`, (c) introducing a new muted strength or
      wash percentage for the quiet marker.
    - Update the Origin line to name this task.

    In `SKILL.md`: refresh the two selected-state bullets (`:47-49`), the accent-reservation
    sentence at `:26` (the accent is now consumed by a live-state selector on the same two
    components), and append a Folded-In Work entry describing this follow-up and its relationship to
    06.6.4.1.1-06's wash. Do NOT restate the full detail there — SKILL.md summarises and points at
    `references/control-density.md`, which carries the contract.

    Accuracy discipline, per the self-caught correction 06.6.4.1.1-06 recorded: do not claim any
    phase closed that `.planning/ROADMAP.md` does not show as closed. This is a quick task on an
    unmerged branch, not a phase closure — say so.
  </action>
  <verify>
    <automated>scripts/run-all-tests.sh; test $? -eq 0</automated>
  </verify>
  <acceptance_criteria>
    1. `grep -c 'SUPERSEDED' .claude/skills/sketch-findings-skypane/references/control-density.md`
       is strictly greater than its pre-change value (recorded before editing).
    2. `grep -c ':has(input:checked)'
       .claude/skills/sketch-findings-skypane/references/control-density.md` is at least `4`.
    3. `grep -c '@supports selector(:has(\*))'
       .claude/skills/sketch-findings-skypane/references/control-density.md` is at least `1`.
    4. The doc names the quiet marker's colour source and it is not the accent:
       `grep -c 'color-mix(in srgb, var(--color-text) 70%, transparent)'
       .claude/skills/sketch-findings-skypane/references/control-density.md` is at least `1`.
    5. The three new "What to Avoid" bullets are present.
    6. `grep -c 'Current' .claude/skills/sketch-findings-skypane/references/control-density.md`
       is at least `1`, and the French alternative appears nowhere:
       `grep -ci 'actuel' .claude/skills/sketch-findings-skypane/references/control-density.md`
       returns `0`. <!-- planner-discipline-allow: actuel -->
    7. `scripts/run-all-tests.sh` is fully green (all 16 harnesses), and
       `server/.venv/bin/ruff check .` is clean.
    8. `git diff --stat` for this task's commit lists exactly the two skill files.
    9. No claim in either file states that phase 06.6.4.1 or any other phase closed as a result of
       this work — cross-checked against `.planning/ROADMAP.md`.
  </acceptance_criteria>
  <done>
    `references/control-density.md`'s "Selected-card treatment" entry describes the shipped
    contract — strong treatment keyed to live `:checked`, server class marking the saved value and
    driving the quiet marker, the `@supports` fallback, the D-03a transfer with its specificity
    arithmetic, the marker-slot asymmetry, and the pseudo-element decision — with the
    `--selected`-keyed version marked SUPERSEDED in place. `SKILL.md`'s summary bullets and
    Folded-In Work list agree with it. The full suite is green.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → companion HTTP | Unchanged by this plan. No new route, no new parameter, no new server-side branch — `companion/pages/config_page.py` and `companion/app.py` both receive a zero diff, so `handle_post()`'s existing `THEME_IDS` / `RUNWAY_IDS` membership validation is untouched. |
| stylesheet → rendered page | The only new surface. CSS gains a text-bearing `content:` property for the first time in this file. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-bbi-01 | Spoofing | The `"Current"` `::after` tag | low | mitigate | The tag's text is a STATIC literal in the stylesheet, never interpolated from `theme_id`, `runway_id` or any request value — so it cannot become an injection or content-spoofing vector. Task 1's acceptance criterion 4 pins the literal to exactly two occurrences, which would fail if anything dynamic were substituted. |
| T-bbi-02 | Tampering | Client-controlled selection display | low | accept | The strong highlight now follows client-side `:checked` state, which a user can trivially change — but that is the intended behaviour and carries no authority: the SAVED value is still whatever the server persisted, still validated server-side on POST, and is still separately rendered via the `--selected` class. A user manipulating their own radio state changes only what their own browser paints. |
| T-bbi-03 | Information disclosure | Rendered theme previews / airport diagrams | low | accept | Unchanged. Both image routes stay behind `require_session()`; this plan touches no route. |
| T-bbi-04 | Denial of service | `:has()` selector cost | low | mitigate | `:has(input:checked)` is scoped to a direct-descendant form control inside at most 16 chips plus 3 cards on one page — a trivially small subject set, well inside the fast path browsers optimise. Task 2's real-browser run is the empirical check: any perceptible interaction lag at 375px would surface there. |
| T-bbi-SC | Tampering | npm/pip/cargo installs | n/a | n/a | No package installs. This plan adds no dependency of any kind — CSS, an existing stdlib-only harness, and two markdown files. The Package Legitimacy Gate does not apply. |
</threat_model>

<verification>
Whole-plan gates, run after Task 3:

- `scripts/run-all-tests.sh` — all 16 harnesses green, coverage at or above the 92% the phase
  recorded.
- `server/.venv/bin/ruff check .` — clean.
- `git rev-parse --abbrev-ref HEAD` still prints `claude/sketch-theme-typography-direction`; no
  branch was created and nothing was rebased onto `main`.
- `git diff --stat <pre-plan-commit>..HEAD` lists exactly four files: `companion/static/style.css`,
  `companion/test_config_page.py`,
  `.claude/skills/sketch-findings-skypane/references/control-density.md`,
  `.claude/skills/sketch-findings-skypane/SKILL.md`.
- `git diff --quiet <pre-plan-commit>..HEAD -- companion/pages/config_page.py
  companion/static/dirty-state.js companion/layout.py companion/app.py server/` exits 0.

<human-check>
Developer look, on the branch, after all three tasks: open Settings in light and dark, click a
different theme chip, and confirm the new choice reads as clearly the selected one while the saved
one reads as a quiet "this is what's saved" marker rather than a second selection. Then Cancel and
confirm it snaps back. The measured evidence is in Task 2's table; this check is about whether the
"Nouveau fort, ancien discret" balance actually feels right at 16-chip density — specifically
whether the dashed muted ring is discreet enough not to compete, and legible enough to be worth
having at all. If the marker reads as noise, the fallback position is to drop the dashed ring and
keep the "Current" tag alone.
</human-check>
</verification>

<success_criteria>
- Clicking, arrow-keying, cancelling and saving all move the strong highlight correctly on BOTH the
  theme picker and the runway picker, proven by recorded `getComputedStyle` measurements in light
  and dark at 1440px and 375px (DP-1, DP-6).
- The saved-but-unchosen card carries an accent-free dashed 70%-muted ring and an English "Current"
  tag; at rest no tag shows anywhere (DP-2).
- `companion/pages/config_page.py` and `companion/static/dirty-state.js` have a zero diff (DP-2's
  "keep the server class", the scope guard, and the no-JavaScript requirement).
- Every live-state rule sits inside `@supports selector(:has(*))`, and all four literal-pinned
  server-class rules survive byte-for-byte so a non-supporting browser still gets today's strong
  treatment (DP-3, H1-H5).
- Two new harness checks prove the live-state layer; the 06.6.4.1.1-06 wash check still passes
  unmodified proving the fallback layer; `EXPECTED_CHECK_COUNT` was re-derived by running (DP-4).
- No new muted strength, no new wash percentage, no new token, no new accent consumer (skill rules).
- `references/control-density.md`'s "Selected-card treatment" entry is superseded in place with the
  live-state re-key, the quiet-marker role, the fallback story and the specificity arithmetic (DP-5).
- Full suite and ruff green; work stayed on `claude/sketch-theme-typography-direction`.
</success_criteria>

<output>
Create `.planning/quick/260904-bbi-selected-state-follows-the-live-choice-n/260904-bbi-SUMMARY.md`
when done. It must include Task 2's full measurement table (not a prose summary of it), the RED
count Task 1 recorded before writing the CSS, the re-derived `EXPECTED_CHECK_COUNT`, and any
comment-prose/grep collision self-caught and reworded along the way (the established convention for
this phase's SUMMARYs).
</output>
