---
phase: quick-260922-jiy
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/static/style.css
autonomous: true
requirements:
  - QUICK-260922-jiy
must_haves:
  truths:
    - "On Compagnies, a visible 24px gap separates the airline gallery grid from the 'Compagnies non identifiees' card below it — the two no longer touch."
    - "The gap-strip's OWN inner grid of unresolved-callsign cards gains no bottom margin of its own — the card's internal rhythm is byte-identical to today."
    - "When a render has no coverage gaps (the strip returns an empty string), no stray margin appears below the gallery at all."
    - "In Heures calmes, a visible 16px gap separates the Nuit/Journee/Toujours actif preset row from the Debut/Fin fields below it."
    - "The three preset buttons stay flush against each other — no gap appears between the segments, and their shared hairline dividers are untouched."
    - "No new CSS custom property, colour literal, font family, size token or class family is introduced; both changes spend existing spacing tokens only."
  artifacts:
    - "companion/static/style.css — one new adjacent-sibling rule and one new declaration on an existing rule"
  key_links:
    - ".illustration-grid + .page-section resolves ONLY to the outer gallery grid followed by the gap-strip card — never to the strip's own .illustration-grid--gap inner grid, which is followed by a <p>, never by a section"
    - "illustration-grid--gap stays a bare modifier with zero rules of its own, as _gap_strip_html()'s docstring promises"
    - "margin-bottom on .quiet-preset-row mirrors .quiet-dial__readout's existing margin: 0 0 var(--space-md) one component above it, so the card reads as one rhythm rather than two"
---

<objective>
Close two developer-reported spacing gaps in the companion app, both already root-caused against the live code: the Compagnies gallery sits flush against the "Compagnies non identifiees" card below it, and the Heures calmes preset row sits flush against the Debut/Fin fields below it.

Purpose: two adjacent blocks with zero space between them read as one run-on region rather than two, on the two pages the developer looks at most.
Output: `companion/static/style.css` — one new narrowly-scoped rule, one new declaration on an existing rule. No Python, no markup, no new tokens.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md

Design-system reference — read the **Spacing** section before writing either value:
`Skill("sketch-findings-skypane")`

Two contracts from that skill govern the two values chosen here, and both are reused rather than invented:
- **Sibling-card gap is `--space-lg` (24px)** — "Every sibling-card gap in the app — in a grid or stacked — is now `--space-lg` (24px), the same value everywhere rather than a mix of gap sizes across contexts" (06.6.4.1.1 D-14/UIR-24). Task 1's pair is exactly that: a grid and the card that follows it.
- **Intra-card row rhythm is `--space-md` (16px)** — established one component above Task 2's target by `.quiet-dial__readout { margin: 0 0 var(--space-md) }`, whose own comment says it "spends an existing spacing token to separate the pair from the preset row below". Task 2 separates that same preset row from the row below it, with the same token.

The seven spacing tokens (`--space-xs` 4 / `sm` 8 / `md` 16 / `lg` 24 / `xl` 32 / `2xl` 48 / `3xl` 64) already exist. **Add no eighth**, and write no bare pixel literal.

**Markup facts, already verified against the tree — do not re-derive:**
- `companion/pages/airlines_page.py` `_gallery_grid_html()` returns `<div class="illustration-grid">…</div>` as its outermost element; `render()` concatenates it immediately followed by `gap_strip_html`, so the two are true DOM siblings.
- `_gap_strip_html()` returns `<section class="page-section">` containing a heading, a caption, its own `<div class="illustration-grid illustration-grid--gap">`, then `overflow_html` — which is a `<p class="text-label section-caption">`. That inner grid is therefore never followed by a `.page-section`.
- `_gap_strip_html()` returns `""` when there are no gaps, in which case the gallery's next sibling is the lightbox `<dialog>` — not a `.page-section`.
- `companion/pages/config_page.py` `quiet_hours_group()` emits `.quiet-preset-row` immediately followed by `.quiet-times-row` as direct siblings.

**The interpreter that runs the harnesses in this worktree is `server/.venv/bin/python`.** Bare `python3` has no Pillow and every harness dies on `import PIL` before running a single check — a failure that looks nothing like a real regression. Baseline, measured before this plan: companion-app 317/317, config-page 274/274, status-pages 316/316, view-pages 169/169.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Separate the Compagnies gallery from the unresolved-callsign card below it</name>
  <files>companion/static/style.css</files>
  <action>
Add ONE new rule to `companion/static/style.css`, placed directly after the existing `.illustration-grid` rule's own `@media (max-width: 959.98px)` block (which ends around line 6253) so the whole gallery-grid story stays in one place: an adjacent-sibling selector matching `.illustration-grid` immediately followed by `.page-section`, declaring `margin-top` of `var(--space-lg)`.

Do NOT put a bottom margin on `.illustration-grid` itself. That class has two consumers — the outer gallery AND the gap-strip's own inner grid (which wears it alongside the `illustration-grid--gap` modifier) — so a generic declaration on it would also push the strip's internal cards away from the overflow line below them, which is not wanted. The adjacent-sibling form is what makes this apply to the outer gallery alone: per the verified markup facts in `<context>`, the inner grid is followed by a `<p>`, so the selector cannot reach it.

Own the direction deliberately: the space is declared as a top margin on the FOLLOWING card rather than a bottom margin on the grid, because the grid is the reused element and the pairing is what needs the space. Margins here do not collapse into anything that would cancel it — `.page-section` establishes its own padded box and the grid is a block-level grid container.

Do NOT add any rule for `illustration-grid--gap`. `_gap_strip_html()`'s docstring states that modifier "carries no rule of its own, present only so a full-page-order check can find the artwork grid's own exact class attribute" — keep that true.

Write the explanatory comment ABOVE the new rule in this file's established voice (cite this plan and the D-14/UIR-24 sibling-card-gap contract, and state why the adjacent-sibling form is load-bearing rather than stylistic). Keep the comment outside the `.illustration-grid` declaration block.
  </action>
  <verify>
    <automated>server/.venv/bin/python -c "
import re
css = re.sub(r'/\*.*?\*/', ' ', open('companion/static/style.css').read(), flags=re.S)
sib = re.search(r'(?&lt;![-\w.#:])\.illustration-grid\s*\+\s*\.page-section\s*\{([^}]*)\}', css)
assert sib, 'the adjacent-sibling rule is absent from the comment-stripped stylesheet'
assert re.search(r'margin-top\s*:\s*var\(--space-lg\)', sib.group(1)), sib.group(1)
own = re.search(r'(?&lt;![-\w.#:])\.illustration-grid\s*\{([^}]*)\}', css)
assert own, 'the base .illustration-grid rule vanished'
assert 'margin' not in own.group(1), 'a margin leaked onto the shared grid class: ' + own.group(1)
assert re.search(r'(?&lt;![-\w.#:])\.illustration-grid--gap\s*\{', css) is None, 'the bare modifier gained a rule'
print('OK')
"</automated>
    <automated>server/.venv/bin/python companion/test_companion_app.py &amp;&amp; server/.venv/bin/python companion/test_status_pages.py &amp;&amp; server/.venv/bin/python companion/test_view_pages.py</automated>
    <human-check>On Compagnies at phone width, the gallery and the "Compagnies non identifiees" card are visibly separated by the same gap that already separates two stacked cards elsewhere; the unresolved-callsign cards INSIDE that card still sit at their original spacing.</human-check>
  </verify>
  <done>
The comment-stripped stylesheet carries `.illustration-grid + .page-section` with `margin-top: var(--space-lg)`; `.illustration-grid`'s own declaration block contains no margin of any kind; `.illustration-grid--gap` still has zero rules; companion-app is 317/317, status-pages 316/316 and view-pages 169/169 (unchanged from baseline, no EXPECTED_CHECK_COUNT edited).
  </done>
</task>

<task type="auto">
  <name>Task 2: Separate the Heures calmes preset row from the Debut/Fin fields</name>
  <files>companion/static/style.css</files>
  <action>
Add a single `margin-bottom` declaration of `var(--space-md)` to the EXISTING `.quiet-preset-row` rule (around line 2987-2992, the block declaring `display: flex`, the hairline border, the radius and `overflow: hidden`). No new rule block, no new selector.

Match `.quiet-dial__readout`'s precedent one component above it in the same file (`margin: 0 0 var(--space-md)`), which separates the dial's readout from this very preset row — the two gaps stacked in one card must be the same size or the card reads as two unrelated rhythms. Use the `margin-bottom` longhand here, not the `margin` shorthand, so the declaration cannot silently zero a horizontal margin the segmented container might later want.

Leave the flush segmented-control look completely untouched: do NOT add `gap` to `.quiet-preset-row`, and do not modify `.quiet-preset-row button` or `.quiet-preset-row button:not(:first-child)`. The absence of separation BETWEEN the three buttons is a deliberate, already-argued design choice — the rule's own comment explains the container-plus-borderless-segment idiom and the `border-left` hairline divider that stands in for a gap. The developer asked for space below the control, not inside it.

Do not touch `.quiet-times-row` or its `@media (max-width: 479.98px)` single-column fallback; the space belongs to the control that owns the pairing, and adding it in both places would double the gap.

Extend the existing comment above `.quiet-preset-row` with one sentence citing this plan and the `.quiet-dial__readout` precedent, rather than opening a second comment block.
  </action>
  <verify>
    <automated>server/.venv/bin/python -c "
import re
css = re.sub(r'/\*.*?\*/', ' ', open('companion/static/style.css').read(), flags=re.S)
row = re.search(r'(?&lt;![-\w.#:])\.quiet-preset-row\s*\{([^}]*)\}', css)
assert row, 'the .quiet-preset-row rule is absent from the comment-stripped stylesheet'
body = row.group(1)
assert re.search(r'margin-bottom\s*:\s*var\(--space-md\)', body), body
assert 'gap' not in body, 'a gap was added between the preset segments: ' + body
assert 'display: flex' in body and 'overflow: hidden' in body, 'the segmented container lost a declaration: ' + body
seg = re.search(r'(?&lt;![-\w.#:])\.quiet-preset-row\s+button:not\(:first-child\)\s*\{([^}]*)\}', css)
assert seg and 'border-left' in seg.group(1), 'the hairline divider between segments was disturbed'
times = re.search(r'(?&lt;![-\w.#:])\.quiet-times-row\s*\{([^}]*)\}', css)
assert times and 'margin' not in times.group(1), 'the gap was double-counted onto .quiet-times-row'
print('OK')
"</automated>
    <automated>server/.venv/bin/python companion/test_config_page.py &amp;&amp; server/.venv/bin/python companion/test_companion_app.py</automated>
    <human-check>In Heures calmes the preset row is separated from Debut/Fin by the same gap that separates the dial's readout from the preset row above it, and the three preset buttons are still visually one control with no space between them.</human-check>
  </verify>
  <done>
`.quiet-preset-row` carries `margin-bottom: var(--space-md)` alongside its original four declarations; it carries no `gap`; the segment `border-left` divider and `.quiet-times-row` are unchanged; config-page is 274/274 and companion-app 317/317 (unchanged from baseline, no EXPECTED_CHECK_COUNT edited).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none crossed) | This change adds two CSS spacing declarations to an already-served static asset. It introduces no route, no input parsing, no template interpolation, no script and no new asset — no untrusted data crosses anything as a result of it. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260922-jiy-01 | Tampering | `companion/static/style.css` | low | accept | The stylesheet is an existing static asset already served over the app's authenticated session; a margin declaration widens no existing exposure, and the file's integrity rests on the same deploy path every prior phase used. No new surface to mitigate. |
| T-260922-jiy-02 | Information disclosure | Compagnies gap strip / Heures calmes card | low | accept | Both changes move already-rendered elements apart. No field is unhidden, no value newly rendered, no `display` or `visibility` touched — `_gap_strip_html()` still returns `""` on a no-gap render, so nothing appears that did not appear before. |
| T-260922-jiy-SC | Tampering | package-manager installs | n/a | n/a | No `pip`, `npm`, `cargo` or any other package install is performed by this plan; the two harness interpreters and Pillow are already present in `server/.venv`. No legitimacy gate applies. |
</threat_model>

<verification>
1. Both automated stylesheet gates pass, read off comment-stripped CSS. Stripping is mandatory, not defensive: this file's comments quote the very selectors and tokens the gates measure, so a raw scan would be satisfied by a paragraph of prose promising a rule nobody wrote. **Both gates were proven non-vacuous during planning** — run against the current unfixed stylesheet they fail (Task 1 on the absent sibling rule, Task 2 dumping the preset row's current five-declaration body), and against a scratch copy carrying both edits they pass. If either gate passes before you have made its edit, the gate itself is broken — fix the gate, do not proceed.
2. All four non-browser harnesses match their pre-change baselines exactly: companion-app 317/317, config-page 274/274, status-pages 316/316, view-pages 169/169. An additive declaration must move no count — if any harness drops, treat it as a real regression rather than an expected-value to bump.
3. `git diff --stat` shows `companion/static/style.css` and nothing else.
4. `companion/test_browser_ux.py` is NOT a usable gate in this worktree: playwright is not installed, so its `main()` prints `SKIP …` and returns 0. Running it proves nothing here — **do not record a SKIP as a pass.** Its two checks that name these selectors were both read and cleared by inspection instead: `_airlines_grid_renders_two_cards_per_row_at_390px()` groups `.airline-card` boxes into rows by their rounded `top` WITHIN each grid and asserts two per row, which a margin between a grid and the following section cannot change; and no check anywhere calls `_css_rule_body()` against `.illustration-grid`, `.page-section` or `.quiet-preset-row`, so no exact-rule-body assertion is exposed to either edit.
</verification>

<success_criteria>
- A visible `--space-lg` gap between the Compagnies gallery and the "Compagnies non identifiees" card, achieved without any margin on the shared `.illustration-grid` class.
- A visible `--space-md` gap between the Heures calmes preset row and the Debut/Fin fields, with the three preset segments still flush.
- Exactly one file changed; zero new custom properties; zero new classes; zero harness check-count edits.
</success_criteria>

<out_of_scope>
Recorded so it is not silently dropped, and deliberately NOT a task here — the batch is bounded to the two reported spacing gaps:

**The accent-reservation list in `style.css`'s own header comment is still two entries short.** `Skill("sketch-findings-skypane")` carries a standing instruction that whichever plan next edits this stylesheet should extend that list by Phase 23's two genuine accent consumers (`.switch[aria-checked="true"] .switch__track`'s fill, and `@keyframes skypane-row-arrive`'s `color-mix` wash). This plan edits the file but adds **no accent consumer of any kind** — both changes are spacing-only — so closing that gap here would be unrelated work riding along in a two-line CSS fix. The instruction stands for the next plan that touches accent colour in this file.
</out_of_scope>

<output>
Create `.planning/quick/260922-jiy-ajouter-de-la-marge-entre-la-galerie-air/260922-jiy-SUMMARY.md` when done.
</output>
