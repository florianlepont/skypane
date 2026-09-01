---
phase: quick-260901-tsa
plan: 260901-tsa
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - companion/layout.py
  - companion/pages/health_page.py
  - companion/static/style.css
  - companion/test_status_pages.py
autonomous: true
requirements: [QUICK-260901-tsa]

must_haves:
  truths:
    - "The Health page carries a one-sentence page purpose directly under its title, rendered through the shared `layout.page_header()`'s ALREADY-EXISTING `purpose` parameter and its already-existing `.page-header__purpose` CSS rule — no new component, no new class, no new CSS rule for this gap."
    - "`layout.page_header()` emits `freshness_html` and `action_html` BEFORE `purpose_html`, so a caller passing both reads title -> action row -> purpose sentence, which is the validated sketch's own DOM order (`<h1>` and the Refresh anchor inside `.page-header`, the purpose paragraph after). Health is the only caller passing both today; Settings/Airlines/History emit byte-identical strings before and after this reorder, because `\"%s%s%s\" % (p, \"\", \"\")` and `\"%s%s%s\" % (\"\", \"\", p)` are the same string."
    - "Each of Health's two section headings is paired with an inline, baseline-aligned muted description inside a new `.section-intro` flex row, reusing the EXISTING `text-label section-caption` class pair quick task 260901-re6 established for exactly this role on Settings — no new muted strength, no new font size, no new colour token."
    - "The `<h2 id=\"...\" class=\"text-heading\">...</h2>` substring for each section is byte-identical to what shipped before, so every existing presence/order/count assertion in `companion/test_status_pages.py` that matches on that exact string keeps passing unmodified."
    - "The Device and ADS-B-pipeline stat tiles no longer print their own caption text a second time inside their body. Each tile is caption + one `<p class=\"stat-tile__value\">` holding `concise_timestamp_html()`'s span — the same caption/value shape the sibling Resolution-rate tile in the same grid already uses, and the same shape the validated sketch's Device and Pipeline tiles use."
    - "Removing those two body dots loses no state signal: `stat_tile()`'s own `status` argument still paints each tile's `--ok`/`--warn`/`--error` top border and tints its icon from the same per-signal value, the two signals are still computed independently (D-12), and the anomaly banner still names each failing category in text."
    - "`.stat-tile__value .mono { font-weight: inherit; }` exists and is load-bearing: `concise_timestamp_html()`'s own `<span class=\"mono\">` carries `font-weight: var(--weight-regular)` from the `.mono` rule, which applies to that span directly and therefore beats the parent's semibold by inheritance — without this scoped rule the Emphasis role is silently inert on both timestamp tiles."
    - "The Screen section's Device tile is wrapped in a `.dashboard-grid`, matching the validated sketch and restoring the `margin-bottom: var(--space-2xl)` that `.dashboard-grid` owns and `.stat-tile` does not declare at all — the standalone tile sat flush against the battery-trend card with literally zero gap."
    - "The battery readout renders BEFORE the chart (sketch order: status chip, readout, chart) and carries the Emphasis role — `var(--font-body-size)` plus `var(--weight-semibold)` — NOT the sketch's literal 28px, which is the Display role 06.6.4 (D-09) deliberately retired along with `--font-display-size` when `.stat-tile__value` and `.runway-card__number` moved to Emphasis."
    - "The readout keeps its `id`, its `mono` class, its `role=\"status\"` live region and its `min-height` reserve, so `companion/static/battery-trend.js`'s `getElementById` lookup, its Left/Right/Home/End roving-tabindex reveal, and the no-layout-jump guarantee all survive the move untouched. `battery-trend.js` is NOT edited."
    - "Every value introduced comes from this stylesheet's own token set — `var(--space-sm)`, `var(--font-body-size)`, `var(--weight-semibold)`, and the existing `.section-caption` 70% muted mix. No new custom property, no new size, no new muted strength, no `:has()` (this file uses none today)."
    - "`companion/test_status_pages.py` passes with `EXPECTED_CHECK_COUNT` moved from its real on-disk baseline to that baseline plus exactly 5, and with three existing count-based checks retargeted IN PLACE (no count change) plus the Section 3 live-HTTP check extended IN PLACE."
    - "`scripts/run-all-tests.sh` reports exactly one failing harness, `server/test_poll_loop.py` (the known, pre-existing, unrelated digest mismatch). No harness that passed before this task fails after it."
    - "A real `companion/app.py` process was started, signed into, and `GET /health` fetched over HTTP with seeded data, confirming the new purpose sentence, both section descriptions, the two timestamp tile values and the repositioned readout render in a genuine response — not only in an in-process `render()` call."
  artifacts:
    - path: "companion/layout.py"
      provides: "`page_header()` emitting freshness/action before purpose, with the reorder's Health-only effect and byte-identical-for-other-callers reasoning documented in the docstring"
      contains: "freshness_block"
    - path: "companion/pages/health_page.py"
      provides: "`PAGE_PURPOSE_TEXT`, `SCREEN_SECTION_DESCRIPTION`, `SERVER_DATA_SECTION_DESCRIPTION`, `_section_intro_html()`; Device/Pipeline bodies as `stat-tile__value`; the Screen `.dashboard-grid` wrapper; the readout moved ahead of the sparkline"
      contains: "section-intro"
    - path: "companion/static/style.css"
      provides: "`.section-intro` + `.section-intro > p`; `.stat-tile__value .mono`; `.battery-readout` promoted to the Emphasis role with its spacing moved from top to bottom"
      contains: ".section-intro {"
    - path: "companion/test_status_pages.py"
      provides: "5 new checks, 3 in-place retargets, 1 in-place live-HTTP extension, and `EXPECTED_CHECK_COUNT` at on-disk-baseline + 5"
      contains: "section-intro"
  key_links:
    - from: "`health_page._section_intro_html()`'s `<div class=\"section-intro\">` wrapper"
      to: "style.css's `.section-intro` flex rule and its `> p` margin reset — the wrapper is inert markup without them, and they are dead CSS without it; Task 3's cross-file DOM-contract guard is what keeps the pair from drifting"
    - from: "`_device_section()`/`_pipeline_section()`'s new `<p class=\"stat-tile__value\">` bodies"
      to: "style.css's `.stat-tile__value .mono { font-weight: inherit; }` — without that one declaration the Emphasis role never reaches the timestamp span and the whole finding-C fix is visually a no-op"
    - from: "`_battery_readout_block()`'s element, now emitted ahead of the sparkline"
      to: "`companion/static/battery-trend.js`'s `document.getElementById(\"battery-readout\")` and its `readout.textContent` writes — position-independent by construction, which is exactly why the move is safe and why that file must not be edited"
    - from: "The Screen section's new `.dashboard-grid` wrapper"
      to: "`_server_data_grid_holds_three_tiles_migrated_cards_outside_grid()`'s `rendered.index('<div class=\"dashboard-grid\">')` — that check silently starts measuring the WRONG grid the moment a second one exists, which is why its retarget is part of Task 2, not Task 3"
---

<objective>
Close the confirmed visual/structural gaps between the shipped Health page (`/health`) and its validated "Merged Health Sketch", found when the developer tested the live page after phase 06.6.4.1's plan 04 shipped.

| # | Gap | Root cause | Fix |
|---|-----|------------|-----|
| A | No page-purpose subtitle under the title | `render()` calls `layout.page_header("Health", freshness_html=...)` and never passes the `purpose` parameter that component has carried since 06.6.2 D-16 | Pass it; add the constant; reorder the component's emission so the purpose sentence lands after the Refresh link as the sketch does |
| B | Both `<h2>` headings are bare — no section description anywhere near either | Never implemented; plan 06.6.4.1-04 emitted the two headings as bare `<h2>`s and no decision ever asked for a description | A `.section-intro` baseline-aligned flex row pairing each heading with a `text-label section-caption` sentence |
| C | Device and Pipeline tiles print their caption text verbatim a second time in their body, and carry no prominent value | Both call `status_dot(state, LABEL)` with the SAME constant the tile caption already renders — two roles, one string | Drop the redundant dot row; promote the timestamp to `<p class="stat-tile__value">`, matching the sibling Resolution-rate tile and the sketch |
| D | Battery readout sits after the chart at 14px muted, not before it as a scannable number | `_battery_readout_block()` classes it `text-label mono`; `_battery_section()` orders it after the sparkline | Move it ahead of the sparkline; promote to the Emphasis role (Body size + semibold), NOT the sketch's retired-Display 28px |
| E | The Screen section's single Device tile sits flush against the battery-trend card, zero gap | Plan 06.6.4.1-04 skipped the `.dashboard-grid` wrapper on a premise ("renders identically at full column width") that is true for WIDTH and silently omits that `.dashboard-grid` owns `margin-bottom: var(--space-2xl)` while `.stat-tile` declares no margin at all | Wrap it, as the sketch itself does |

Purpose: make the shipped Health page match what the developer actually validated, so 06.6.4.1's closing checkpoint can sign the page off as built rather than as intended.

Output: two markup/copy edits in `health_page.py`, one emission-order edit in `layout.py`, four style.css rule changes (two new, two edited), 5 new harness checks, 3 in-place retargets, 1 in-place live-HTTP extension.

**Approach note — translate the sketch, never transplant it.** The sketch is a standalone HTML file with its own private token block; several of its values are ones this project has since deliberately moved past. Two are load-bearing here and are handled explicitly below: its `.battery-readout` 28px is the **Display role 06.6.4 (D-09) retired** (`--font-display-size`; its two consumers moved to Emphasis — Body size plus semibold), and its `--color-text-muted` **token does not exist in this stylesheet at all** (style.css says so in its own words at the History merged-cell comment — "inventing a new token, or hard-coding a grey, would be wrong in one of the two themes"). Where a sketch value has been superseded, ship the project's current equivalent and say so in the comment; do not resurrect a retired role to match a mockup.

**Non-goals — verified, deliberately NOT touched.**
- **The anomaly banner.** `.banner--anomaly` with its `banner__pill` chips already implements the pill-based short-label pattern (D-07). Confirmed correct; do not touch it or `_anomaly_banner_html()`.
- **The Unresolved-prefixes and Resolution-statistics cards.** They use `.page-section` where the sketch used `.wide-card`; `.page-section` is this project's current card class for exactly that role (D-11), so this is a naming difference, not a deviation. Their internal `resolution-grid`-equivalent structure is already faithful. Do not touch them, `_registry_section()`, `_registry_filter_bar_html()`, `_registry_table_html()` or `_stats_table_html()`.
- **The Corroboration tile.** The sketch shows it as caption + one `stat-tile__value` + details. The shipped tile is caption + three per-state count rows + a `readings-disclosure`. That is D-15's genuine three-state breakdown (Agreement / Single-source / Disagreement, each with its own count and its own dot) — a deliberate refinement past the sketch's single-value mockup, and its three dot labels are all DIFFERENT from its caption, so it has none of finding C's duplication. Leave it exactly as it is.
- **`.freshness-refresh`.** It genuinely has no CSS rule in style.css today, so the Refresh link renders as a default 16px accent link where the sketch shows 14px muted. This is deliberately left alone: style.css's own header keeps an exhaustive register of approved accent uses and "links" is explicitly on it, so an accent Refresh link is compliant with the current design system rather than a defect; muting it would also introduce a new muted-text-on-canvas pair that `companion/test_contrast_check.py`'s `live_pairs` would need to cover. Record it in the SUMMARY as an observed sketch difference the developer can call, not a gap this task closed.
- **`.page-header` as a flex row.** The sketch makes it `display: flex; justify-content: space-between` so Refresh sits right-aligned on the title's row. Not done here: the purpose paragraph lives INSIDE that div for all four pages, so flexing it would sit Airlines' and History's purpose sentences beside their titles. Making the sketch's arrangement possible needs a DOM change to a component four pages share — a design decision, not a gap closure.
- **`companion/static/battery-trend.js`.** Not edited. The readout move is safe precisely because that file looks the element up by id.
- **`companion/pages/airlines_page.py`, `history_page.py`, `config_page.py`.** Not edited. `layout.page_header()`'s reorder is proven byte-identical for all three by Task 1's own verify gate.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./.claude/CLAUDE.md

@companion/pages/health_page.py
@companion/layout.py
@companion/static/style.css
@companion/test_status_pages.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add the page purpose and the two section-intro descriptions</name>
  <files>companion/layout.py, companion/pages/health_page.py, companion/static/style.css</files>
  <read_first>
    - `companion/layout.py::page_header()` in full, including its "THIS SIGNATURE IS A LITERAL CONTRACT" docstring paragraph — read exactly what that contract covers (the parameter names and their order) versus what it does not (the order the four blocks are concatenated into the returned string).
    - The four `layout.page_header(` call sites: `health_page.py`, `airlines_page.py`, `config_page.py`, `history_page.py`. Confirm for yourself that Health is the only one passing both a purpose and a freshness/action block.
    - style.css's `.page-title`, `.page-header__purpose` and `.page-header` rules (they sit together, just after the heading-rhythm rule) — note that `.page-header` is a plain block with no padding and no border, which is what lets a last-child purpose paragraph's bottom margin collapse with the parent's.
    - style.css's `.text-label` and `.section-caption` rules AND the whole comment block above `.section-caption` — especially its final sentences, which state that the absence of a margin declaration there is a decision and must not be "completed". This task must honour that rule while still zeroing the paragraph's margin inside the new flex row; read it before deciding where the zeroing lives.
    - style.css's `h1, h2, h3, .text-heading { margin: 0 0 var(--space-sm); }` heading-rhythm rule and the comment above it.
    - `health_page.py::render()`'s tail (the `screen_section_html` / `server_data_section_html` construction and the final concatenation) and the `SCREEN_SECTION_ID` / `SERVER_DATA_SECTION_ID` / heading constants block above it.
    - `companion/test_status_pages.py::_health_page_two_id_anchored_sections_correct_order_no_overview()` — it matches on the FULL `<h2 id="..." class="text-heading">...</h2>` string and counts `'<h2 id="'` occurrences. Nothing this task does may change either.
  </read_first>
  <action>
**A. `layout.py` — emission order.** In `page_header()`, move `freshness_block` and `action_block` ahead of `purpose_html` in the returned string's interpolation. Change nothing else: not the signature, not the parameter order, not the escaping of `title`/`purpose`, not the pass-through-verbatim contract on the other two.

Extend the docstring with a short paragraph recording why. The validated Health sketch's own header markup is the title and the Refresh anchor inside one `.page-header` element, with the purpose sentence following after it — so the purpose sentence is the last thing before page content, not something wedged between the title and its action link. State plainly that the LITERAL CONTRACT paragraph above covers the signature (names and their order), which this edit does not touch, and that the emission order is a separate thing. Record the blast radius honestly: Health is the only call site today passing both a purpose and a freshness block, and for a caller passing exactly one of the three optional blocks the concatenation produces the identical string either way, so Settings, Airlines and History are byte-identical before and after — this is a Health-only visual change. Note too that with the purpose paragraph now the last in-flow child of a block-level `.page-header` that has no padding and no border, its own bottom margin collapses with the parent's, so the gap below the header is unchanged rather than doubled.

**B. `health_page.py` — the three new copy constants.** Next to the existing `SCREEN_SECTION_*` / `SERVER_DATA_SECTION_*` block, add three module constants carrying the sketch's own validated copy verbatim:
- a page-purpose sentence: `Screen status and server data quality, in one place.`
- a Screen description: `— the physical frame: is it checking in, and how's the battery.`
- a Server-&-data description: `— the ADS-B pipeline and route resolution: is the data fresh and trustworthy.`

Keep the leading em-dash and the space after it on both descriptions — that is what makes the heading and its description read as one continuous phrase across the baseline-aligned row, and it is the validated copy. Comment the block: this is the sketch's own wording, and the two descriptions restate the split D-10 already made (the physical frame versus the ADS-B/route-resolution pipeline) in the reader's own terms rather than making a new claim.

**C. `health_page.py` — pass the purpose.** Add `purpose=` to the existing `layout.page_header("Health", ...)` call, keeping `freshness_html` exactly as it is.

**D. `health_page.py` — the section-intro builder.** Add one small private builder taking a section id, a heading string and a description string, returning a single `<div class="section-intro">` containing the heading `<h2>` and then a `<p>` classed with the existing `text-label section-caption` pair. The `<h2>` it emits must be byte-identical to the string `render()` builds today — same attribute order (`id` then `class`), same class value, same `escape_html()` on the heading text — because the existing structural check matches that whole string literally and counts `'<h2 id="'` occurrences. Escape the description through `escape_html()` at the point of interpolation, the single-escaping-choke-point discipline this module documents.

Give it a docstring: the wrapper exists so the description sits inline and baseline-aligned with its heading rather than as a separate stacked paragraph; the `text-label section-caption` class pair is reused rather than reinvented because quick task 260901-re6 already established exactly that pair for the muted one-sentence-under-a-heading role on Settings, and a second class for the same role would reopen the second-muted-strength defect this stylesheet's own comments record having fixed twice.

Then replace the two hand-built `<h2 ...>` strings in `render()`'s `screen_section_html` / `server_data_section_html` with calls to this builder. Everything after each heading in both sections stays exactly where it is.

**E. `style.css` — the `.section-intro` pair.** Add two rules immediately after the `.section-caption` rule, so the role rule and the container rule that overrides one of its stated decisions are read together.

The first, `.section-intro`, is a wrapping flex row with its items aligned on their shared baseline and `var(--space-sm)` between them. It deliberately declares NO margin of its own: the `<h2>` inside it still carries the heading-rhythm rule's `margin: 0 0 var(--space-sm)`, and a flex item's own margin still contributes to its line, so the gap below the whole row is exactly the gap that existed below the bare `<h2>` before this change. Say that in the comment — a reader must be able to tell that the unchanged spacing is the intent, not an omission — and say that the wrap is what lets the description drop onto its own line on a narrow viewport instead of squeezing the heading.

The second, `.section-intro > p`, zeroes the paragraph's margin. Comment it explicitly against the `.section-caption` rule directly above: that rule's own comment states its lack of a margin declaration is a decision, because in its Settings context the caption is an ordinary block sibling relying on the UA paragraph margin the validated sketch was measured against. That reasoning is context-specific, so the zeroing belongs here on the container — where the flex row owns the layout — and not as a new declaration inside `.section-caption`, which would silently change every Settings group at the same time. Use the child combinator, not a descendant selector: only the row's own direct paragraph is being laid out.
  </action>
  <verify>
    <automated>test "$(awk '/^\.section-intro \{/,/^\}/' companion/static/style.css | grep -cE 'display: flex|align-items: baseline|gap: var\(--space-sm\)|flex-wrap: wrap')" = 4 && test "$(awk '/^\.section-intro > p \{/,/^\}/' companion/static/style.css | grep -c 'margin: 0')" = 1 && server/.venv/bin/python3 -c "import sys, tempfile, shutil; sys.path.insert(0, '.'); from companion.pages import health_page as h; from companion import layout; from companion.pages import airlines_page as a, config_page as c; d = tempfile.mkdtemp(); r = h.render({'state_dir': d}); shutil.rmtree(d, ignore_errors=True); assert r.count('class=\"section-intro\"') == 2, 'section-intro count'; assert r.count(layout.escape_html(h.PAGE_PURPOSE_TEXT)) == 1, 'purpose count'; assert r.count('<h2 id=\"') == 2, 'id-anchored h2 count'; assert layout.escape_html(h.SCREEN_SECTION_DESCRIPTION) in r, 'screen description'; assert layout.escape_html(h.SERVER_DATA_SECTION_DESCRIPTION) in r, 'server-data description'; assert r.index('freshness-refresh') < r.index(layout.escape_html(h.PAGE_PURPOSE_TEXT)), 'refresh must precede the purpose sentence'; assert layout.page_header('X', purpose='P') == layout.page_header('X', purpose='P'), 'stable'; assert '<p class=\"page-header__purpose text-body\">P</p></div>' in layout.page_header('X', purpose='P'), 'purpose-only callers unchanged'; print('markup ok')" && server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_config_page.py && server/.venv/bin/python3 companion/test_view_pages.py</automated>
  </verify>
  <done>
`layout.page_header()` emits freshness/action before purpose with the reorder documented and proven harmless for purpose-only callers; `health_page.py` carries the three new copy constants, passes the purpose, and builds both section headings through one `.section-intro` builder whose `<h2>` string is byte-identical to before; style.css carries `.section-intro` and `.section-intro > p` placed next to `.section-caption` with the margin-ownership reasoning written down. All three companion page harnesses pass at their unchanged `EXPECTED_CHECK_COUNT`s.
  </done>
</task>

<task type="auto">
  <name>Task 2: Give the two timestamp tiles a real value, wrap the Screen tile in a grid, and lift the battery readout above the chart</name>
  <files>companion/pages/health_page.py, companion/static/style.css, companion/test_status_pages.py</files>
  <read_first>
    - `health_page.py`'s module docstring, specifically the "Two independent freshness signals (D-12, 06-RESEARCH.md Open Question 2)" paragraph — this task must leave that claim true and must update its wording where it stops being literally accurate.
    - `_device_section()`, `_pipeline_section()`, `_unavailable_block()` and `layout.status_dot()` — note that `status_dot()` always emits a `dot-label` span, which is why "keep the dot, drop only its text" is not available without either duplicating `_STATUS_DOT_CLASSES` or emitting an empty span.
    - `layout.stat_tile()` in full — read how `status` maps to the `stat-tile--ok/warn/error` modifier and how `icon` is tinted from that same modifier, so you can see for yourself that the tile already carries each signal's state twice in colour before any body dot is added.
    - `layout.concise_timestamp_html()` — it returns `<span class="mono" title="...">HH:MM UTC (Nm ago)</span>`, already-safe markup that must never be re-escaped.
    - style.css's `.mono`, `.stat-tile__value`, `.stat-tile`, `.dashboard-grid` and `.battery-trend-section` rules, plus the retired-Display-role paragraph in the `.site-title` comment (`--font-display-size was retired ... restoring the scale block above to its own claimed four sizes`). `.mono` declares `font-weight: var(--weight-regular)`; `.dashboard-grid` declares `margin-bottom: var(--space-2xl)`; `.stat-tile` declares no margin at all. All three facts are load-bearing below.
    - style.css's `.battery-readout` rule and the comment above it (the reserved-height / no-layout-jump reasoning).
    - `health_page.py::_battery_readout_block()`, `_battery_section()`'s `chart_block` assembly, and `companion/static/battery-trend.js` in full — enough to satisfy yourself that the readout is found by id, that `role="status"` is the live-region announcement channel for the Left/Right/Home/End roving-tabindex traversal, and that nothing in that file depends on the element's position in the document.
    - `render()`'s `§5.2 (D-10)` comment above `screen_section_html`, in full.
    - The three checks this task WILL break, all in `companion/test_status_pages.py`: `_independent_thresholds_one_warn_one_ok()`, `_battery_badge_present_and_healthy_on_normal_trend()`, and `_server_data_grid_holds_three_tiles_migrated_cards_outside_grid()`. Retargeting them is part of THIS task, not Task 3.
  </read_first>
  <action>
**A. Device and Pipeline tile bodies.** In `_device_section()` and `_pipeline_section()`, replace the body row's `status_dot(...) + detail` pair with a single `<p class="stat-tile__value">` holding `detail` (the `concise_timestamp_html()` return value) and nothing else. Interpolate it verbatim — no `escape_html()`, for the reason the existing D-09 comment beside it already gives. Leave both functions' `_DB_UNAVAILABLE` branches alone: `_unavailable_block()`'s sentence is prose, not a value, and stays a `text-body` paragraph. Leave both returned `state` values and both signatures alone.

Comment both edits with the same finding: the tile caption and the dot label were being handed the SAME module constant, so each tile printed its own name twice, one line under the other — the caption row naming the signal and the body row naming it again before the timestamp. The caption is the tile's title role and stays; the body's job is to answer it. Record explicitly that dropping the dot does not drop the signal — `stat_tile()`'s `status` argument still paints this tile's status-coloured top border and tints its icon from the same per-signal value, so the state is still carried twice in colour without a third carrier, and `collect_anomalies()` still names the failing signal in text. Note that keeping a dot while dropping only its text was considered and rejected: `status_dot()` always emits a label span, so it would mean either an empty span or a second copy of that function's status-to-class mapping.

Then update the module docstring's D-12 paragraph so it stays literally true: the two signals are still genuinely different, still computed from different sources, still never blended into one verdict, and each still renders its own independent ok/warn/error state — now through its own tile's status modifier rather than through a dot inside the tile body.

**B. The scoped Emphasis reach-through.** Add `.stat-tile__value .mono { font-weight: inherit; }` to style.css, immediately after the `.stat-tile__value` rule. This is not cosmetic tidying — without it part A is a visual no-op. Comment it with the exact mechanism: `.stat-tile__value` sets the Emphasis weight on the paragraph, but the value it now holds is a `<span class="mono">`, and `.mono` sets `font-weight: var(--weight-regular)` on that span directly. A rule that targets an element beats a weight the element would otherwise inherit, regardless of the two selectors' equal specificity, so the span silently renders regular and the promotion never appears on screen. `inherit` is what lets the parent's weight through while leaving `.mono`'s family (the whole reason the span exists — stable digit widths in a value that changes on hover) intact. Cross-reference the `.filter-bar__field input` rule as this file's established precedent for a narrow, scoped opt-out of a global rule for one container's descendants, and state that this rule is scoped to `.stat-tile__value` on purpose: mono values elsewhere in the file keep `.mono`'s regular weight.

**C. Wrap the Screen section's Device tile in a `.dashboard-grid`.** In `render()`, wrap `device_tile_html` in a single `<div class="dashboard-grid">` ... `</div>`, still between the Screen heading and the battery-trend section.

Rewrite the `§5.2 (D-10)` comment's Screen sentence. Its current premise — that a single-tile grid row and a bare block-level tile render identically at full column width — is true about WIDTH and is exactly why this shipped, but it silently omits spacing: `.dashboard-grid` declares `margin-bottom: var(--space-2xl)` and `.stat-tile` declares no margin at all, so the standalone tile sat flush against the battery-trend card below it with zero gap while the Server & data grid kept its 48px. State that, and note that the validated sketch itself wraps its own single Device tile in a `dashboard-grid` for the same reason. Leave the D-11 half of that comment (page-section, never stat-tile/dashboard-grid, for the wide-table-in-a-240px-track failure mode) exactly as written — it is about a different container and is still correct.

**D. Lift the battery readout above the chart.** In `_battery_section()`, reorder `chart_block` so the readout block comes first, then the sparkline, then the script tag. The script tag stays last and stays on the chart-bearing branch only, so the "exactly one script tag, and zero on the no-chart path" guarantee is untouched.

In `_battery_readout_block()`, drop `text-label` from the element's class list, keeping `battery-readout mono`, the `id`, `role="status"`, and the seeded latest-reading text exactly as they are.

Extend that function's docstring: the readout is now the section's scannable headline number and sits ahead of the chart, matching the validated sketch's order (status chip, readout, chart); `text-label` is gone because that class pinned it to the 14px Label role, which is the opposite of the role it now plays. Record the two things that deliberately did NOT change and why each matters — `role="status"` is the live region `battery-trend.js` announces every Left/Right/Home/End traversal through, and the element is still found by `getElementById`, so its position in the document was never something that file depended on. Say plainly that `battery-trend.js` is not edited by this task.

**E. Promote `.battery-readout` to the Emphasis role.** Edit the existing rule: add the Body size and the semibold weight, keep the `min-height` reserve unchanged, and move its margin from top-only to bottom-only using `var(--space-sm)` — the spacing it owns moved with it when the element moved from below the chart to above it.

Comment the change with three points a future reader needs. First, why this is Emphasis and not the sketch's own 28px: 28px is the Display role, which 06.6.4 (D-09) retired outright along with `--font-display-size` when `.stat-tile__value` and `.runway-card__number` both moved to Emphasis — restoring this file's claimed four-size scale — so matching the mockup literally would resurrect a deliberately-retired role and re-break that claim. Emphasis is this project's current answer to "make one number the scannable one", and it is the same role the `.stat-tile__value` tiles on this very page now use. Second, that the weight here beats `.mono`'s regular by source order, not by specificity — both are single-class selectors landing on the same element, and this rule is later in the file — so this rule must stay after `.mono`; Task 3 pins that with a check rather than leaving it to a comment. Third, that the `min-height` reserve stays in `em`, so it scales with the new size on its own and the no-layout-jump guarantee its original comment describes still holds; note that the reveal text is fixed-width by construction (a 4-digit millivolt figure plus a fixed-length ISO timestamp, in a monospace face), so a reveal cannot change where the line wraps and therefore cannot shift the chart now sitting below it.

**F. Retarget the three checks this task breaks, IN PLACE.** No `EXPECTED_CHECK_COUNT` movement in this task — Task 3 owns that.

- `_independent_thresholds_one_warn_one_ok()` seeds a stale device and a fresh pipeline and counts status-dot classes. Those two dots no longer exist, so retarget the check onto the signal that now carries the same information: assert that the Device tile's wrapper carries the error modifier and the Pipeline tile's carries the ok modifier, locating each by its own caption constant inside the tile's slice so the check cannot pass by matching the wrong tile. Keep a dot-class assertion for the dots that legitimately remain (the battery badge and the migrated registry card's Coverage dot) rather than deleting that half. Derive every count in the rewritten check by RUNNING it against the real fixture — do not carry a number over from this plan's prose. Update the check's `check(...)` description and its inline comment to say what it now proves: the two thresholds are still independent, and each signal's state is now read from its own tile modifier.
- `_battery_badge_present_and_healthy_on_normal_trend()` asserts an exact healthy-dot count on an all-fresh fixture. Two of the dots it counted are gone. Update the number to the real value observed by running it, and rewrite its inline comment to enumerate which dots remain and why, in the same style the existing comment uses. Its negative assertion (no warn/error class in this fixture) stays as-is — it is still true and still meaningful.
- `_server_data_grid_holds_three_tiles_migrated_cards_outside_grid()` is the dangerous one: it locates the grid with a plain first-occurrence index, which now finds the Screen section's grid instead of the Server & data one and would quietly measure the wrong slice. Anchor its search to the Server & data heading's own offset so it always measures the intended grid, update the expected total grid count, and update the inline comment that currently describes the Device tile as standalone. Add an assertion inside this same check that the Screen section's grid holds exactly one tile — that is the new invariant Task 2C introduces and it belongs beside the one it mirrors. The total stat-tile count across the page does not change.

After each of A through F, run `server/.venv/bin/python3 companion/test_status_pages.py` before moving to the next — a retarget written against an unrun change is a guess.
  </action>
  <verify>
    <automated>test "$(awk '/^\.stat-tile__value \.mono \{/,/^\}/' companion/static/style.css | grep -c 'font-weight: inherit')" = 1 && test "$(awk '/^\.battery-readout \{/,/^\}/' companion/static/style.css | grep -cE 'font-size: var\(--font-body-size\)|font-weight: var\(--weight-semibold\)|min-height|margin: 0 0 var\(--space-sm\)')" = 4 && server/.venv/bin/python3 -c "import sys; sys.path.insert(0, '.'); s = open('companion/static/style.css').read(); assert s.index('.mono {') < s.index('.battery-readout {'), 'the Emphasis weight relies on .battery-readout following .mono in source order'; print('source order ok')" && server/.venv/bin/python3 -c "import sys, tempfile, shutil; sys.path.insert(0, '.'); from companion.pages import health_page as h; d = tempfile.mkdtemp(); r = h.render({'state_dir': d}); shutil.rmtree(d, ignore_errors=True); assert r.count(h.DEVICE_FRESHNESS_LABEL) == 1, 'device label must appear exactly once on the page'; assert r.count(h.PIPELINE_FRESHNESS_LABEL) == 1, 'pipeline label must appear exactly once on the page'; assert r.count('<div class=\"dashboard-grid\">') == 2, 'two dashboard grids'; assert r.count('class=\"stat-tile ') == 4, 'still four stat tiles'; g = r.index('<div class=\"dashboard-grid\">'); assert r[g:r.index('</div>', r.index('class=\"stat-tile ', g))].count('class=\"stat-tile ') == 1, 'the Screen grid holds one tile'; print('markup ok')" && server/.venv/bin/python3 -c "
import sys, tempfile, shutil; sys.path.insert(0, '.')
from datetime import datetime, timedelta, timezone
from server import history_db as hd
from companion.pages import health_page as h
d = tempfile.mkdtemp(); n = datetime.now(timezone.utc)
with hd.open_db(d) as conn:
    for off, mv in ((2, 4200), (1, 4190)):
        hd.record_device_health(conn, (n - timedelta(minutes=off)).isoformat(timespec='seconds'), battery_mv=mv)
r = h.render({'state_dir': d}); shutil.rmtree(d, ignore_errors=True)
assert 'class=\"battery-readout mono\"' in r, 'readout class list'
assert 'role=\"status\"' in r, 'live region survives'
assert r.index(h.BATTERY_READOUT_ID) < r.index('<svg'), 'readout must precede the chart'
assert r.index('<svg') < r.index('<script'), 'script still follows the chart'
print('readout ok')
" && server/.venv/bin/python3 companion/test_status_pages.py</automated>
  </verify>
  <done>
Neither freshness label appears twice on the rendered page; both timestamp tiles are caption + one `stat-tile__value` paragraph; `.stat-tile__value .mono` lets the Emphasis weight reach the timestamp span; the Screen section holds a one-tile `dashboard-grid` and the page holds two grids and still four tiles; the readout renders ahead of the chart with `battery-readout mono`, `role="status"` and the Emphasis role, with the script tag still after the chart; `battery-trend.js` is untouched; all three broken checks are retargeted in place and `companion/test_status_pages.py` passes at its still-unchanged `EXPECTED_CHECK_COUNT`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Pin all five fixes with harness checks, run the full suite, and verify against a real running service</name>
  <files>companion/test_status_pages.py</files>
  <read_first>
    - `companion/test_status_pages.py`'s `EXPECTED_CHECK_COUNT` and the whole provenance comment block above it — read the REAL on-disk value at execution time; this plan deliberately names no number.
    - The `check(name, fn)` helper at the top of `main()` for the return-tuple contract, and `_mkstate` / `_ctx` / `_iso` / `_now` / `_seed_device_health` / `_seed_meta` / `_seed_unresolved_prefixes` / `_seed_runway_events`.
    - `_health_page_opens_with_shared_page_header()` — the new page-purpose check belongs immediately after it.
    - `_health_page_two_id_anchored_sections_correct_order_no_overview()` — the new section-intro check belongs immediately after it.
    - `_battery_section_class_is_styled_in_stylesheet()` — the existing, weaker cross-file guard; the new one reuses its file-read approach but asserts declarations inside a located rule body, not bare substring presence.
    - Section 3's `Harness` block and its `_both_tabs_ok_end_to_end()` check — this task extends that existing check in place rather than adding a second live one.
    - `companion/test_config_page.py`'s cross-file DOM-contract guard block for the index-plus-window slicing idiom (locate a selector with `source.index(...)`, slice to the next closing brace, assert the expected declaration is inside the slice — never a regex CSS parser).
  </read_first>
  <action>
Add exactly five checks, extend one in place, and bump the count.

**Check 1 — the page purpose.** Immediately after `_health_page_opens_with_shared_page_header()`. Render Health and assert: the escaped `PAGE_PURPOSE_TEXT` appears exactly once; it appears inside the `.page-header` div (slice from that div's opening tag to its matching close and assert containment there, not anywhere on the page); and its offset is after the Refresh link's, which is the sketch's own DOM order. Reference the constant through `layout.escape_html()` — never re-type the sentence; this harness must not become a second place that copy lives.

**Check 2 — the two section intros.** Immediately after `_health_page_two_id_anchored_sections_correct_order_no_overview()`. Assert: exactly two `section-intro` wrappers; each one contains its own section's `<h2>` and its own escaped description constant, matched by slicing each wrapper rather than searching the whole page; and each description's offset falls after its own heading's. Build every expected substring from the module constants through `escape_html()` — the Screen description contains an apostrophe, which `escape_html(..., quote=True)` encodes, so a raw-constant comparison would fail for a reason that has nothing to do with the markup being right. Say so in an inline comment; it is the single likeliest way this check gets "fixed" wrongly later.

**Check 3 — no duplicated tile labels, and a real value in each.** Place it near the existing freshness-label checks. Assert, for each of the two freshness constants: the constant appears exactly once in the whole rendered page; the tile whose caption carries it also carries exactly one `stat-tile__value` paragraph in its own slice; that paragraph holds a `mono` timestamp span; and no `dot-label` appears inside that tile's slice. Fail with a message naming which of the two tiles failed and which sub-assertion, so a regression is diagnosable from the output alone.

**Check 4 — the readout's position, class list and live region.** Place it beside the existing battery-readout checks. On a two-reading fixture, slice to the battery-trend section's own boundaries (its opening tag through its matching `</section>`, the same technique `_battery_section_keeps_everything_after_the_move()` already uses) and assert within that slice: the readout element's offset precedes the sparkline `<svg>`'s; the sparkline's precedes the `<script`'s; the element's class list is exactly the two expected classes; and `role="status"` is present. Assert as well that `companion/static/battery-trend.js` still looks the element up by `BATTERY_READOUT_ID`'s literal value — the property that makes the reposition safe.

**Check 5 — cross-file CSS DOM-contract guard.** Place it beside `_battery_section_class_is_styled_in_stylesheet()`, reading the stylesheet the same way that check does. For each selector this page module now depends on, locate it with `source.index(...)`, slice to the next closing brace, and assert the expected declaration is inside that slice: `.section-intro` sets a flex display; `.section-intro > p` zeroes its margin; `.stat-tile__value .mono` inherits its font weight; `.battery-readout` sets the semibold weight. Then assert the one source-order fact the Emphasis promotion actually rests on — that `.mono`'s rule appears before `.battery-readout`'s in the file — with a failure message saying in words that moving `.battery-readout` above `.mono` would silently return the readout to regular weight. Fail with a message naming which selector or which declaration is missing, matching the neighbouring guards' error style.

**In-place extension — the live-HTTP check.** Extend Section 3's existing `_both_tabs_ok_end_to_end()` rather than adding a new check (no count change): after its existing per-route status and heading assertions, for the `/health` response body only, assert that the escaped page purpose and both escaped section descriptions are present, and that neither freshness-label constant appears more than once. This is the automated half of "verified against a real running service" — a real subprocess, a real login, a real seeded database, a real HTTP response. Update the `check(...)` description to say so.

**Falsifiability pass.** Before finalizing, mutate all five new checks at once so each asserts on a name that does not exist in the source it reads, run the harness, and confirm the output reports exactly those five as FAIL and nothing else. Then restore them. A check that cannot be observed failing is not a check.

**Count bump.** Read the current on-disk `EXPECTED_CHECK_COUNT` and set it to that value plus exactly 5. Do not carry a number over from this plan text. Extend the provenance comment block above it with one new entry in that block's own established format: name this quick task, list the five checks added, and record that Task 2's three retargets and this task's live-HTTP extension were all in place with no count change.

**Full suite.** Run `scripts/run-all-tests.sh`. The only harness in its FAILED list must be `server/test_poll_loop.py` — the known, pre-existing, unrelated digest mismatch. If any other harness fails, or if the coverage gate reports a new shortfall, stop and fix it before finishing this task; do not record a green result over a new failure.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py && test "$(server/.venv/bin/python3 companion/test_status_pages.py | tail -1 | sed 's#.*: \([0-9]*\)/\([0-9]*\).*#\1-\2#')" = "$(grep '^EXPECTED_CHECK_COUNT = ' companion/test_status_pages.py | sed 's/.*= //' | awk '{print $1"-"$1}')" && scripts/run-all-tests.sh > /tmp/skypane-tsa-run-all-tests.log 2>&1; test "$(sed -n '/FAILED harnesses/,$p' /tmp/skypane-tsa-run-all-tests.log | grep -c '^    - ')" = 1 && sed -n '/FAILED harnesses/,$p' /tmp/skypane-tsa-run-all-tests.log | grep -q 'server/test_poll_loop.py'</automated>
    <human-check>
REQUIRED, not optional — this project's own memory records that computed-style and structural checks alone have already missed a real rendered bug once (`feedback_real_device_ui_verification`). Start a throwaway service against a seeded state directory (`SKYPANE_COMPANION_PASSWORD=&lt;any&gt; server/.venv/bin/python3 companion/app.py --port &lt;free&gt; --state-dir &lt;tmpdir&gt;`), sign in, and open `/health` in a real browser with real battery/pipeline data present — at a desktop width and again at roughly 375px, in both themes.

Confirm by eye:
1. A muted one-sentence purpose line sits under the "Health" title, with the Refresh link above it, and the gap below the header block is unchanged from before this task.
2. Each of "Screen" and "Server &amp; data" has its description sitting on the same baseline as the heading at desktop width, and dropping cleanly onto its own line at 375px without crowding the heading.
3. Neither the Device tile nor the ADS-B pipeline tile prints its own name twice. Each reads as a caption followed by one clearly heavier timestamp — and that timestamp is visibly bolder than the surrounding label text, which is the whole point of the `.stat-tile__value .mono` rule; if it looks the same weight as before, that rule is not landing.
4. There is a real, generous gap between the Device tile and the Battery-trend card below it, matching the gap under the Server &amp; data grid.
5. The battery voltage readout sits above the chart as the section's most scannable number, and hovering, tapping, and arrowing (Left/Right/Home/End) through the chart points still updates it in place without the chart shifting.
6. A stale device still reads unambiguously as a problem: the tile's top border and its icon are still status-coloured even though the body dot is gone.

Stop the process and delete the tmpdir afterwards. Record what was actually observed in the SUMMARY — including any point that could not be exercised (e.g. no stale-device fixture available) — rather than restating this list as if performed.
    </human-check>
  </verify>
  <done>
`companion/test_status_pages.py` passes with every check green, its printed total equals the new `EXPECTED_CHECK_COUNT`, and that value is the real on-disk baseline plus exactly 5. The provenance comment records this task's five additions, Task 2's three in-place retargets, and the in-place live-HTTP extension. Each new check was observed failing under mutation before being restored. `scripts/run-all-tests.sh` lists exactly one failing harness, `server/test_poll_loop.py`. The live browser pass was performed and its real observations are recorded in the SUMMARY.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser -> `GET /health` | Server-rendered HTML reaches an authenticated operator's browser. Every dynamic value on this page already passes through `escape_html()` or one of `companion/layout.py`'s escaping component builders. |
| `history_db` / `poll_loop` state files -> `render()` | Device telemetry, pipeline meta and the hand-editable unresolved-prefix registry. Untouched by this plan; every read still goes through `_safe_query()` or `unresolved_rows()`'s own defensive parse. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-tsa-01 | Tampering (XSS) | The three new copy constants and the `_section_intro_html()` builder | low | mitigate | All three are module-level string literals, never interpolated from request or database data, and each still reaches HTML through `escape_html()` at the point of interpolation — the single-escaping-choke-point discipline this module documents. No new raw-markup parameter is introduced anywhere. Task 1's verify gate compares the rendered output against `escape_html(constant)`, so a builder that forgot to escape would fail the gate. |
| T-tsa-02 | Tampering (XSS) | `_device_section()` / `_pipeline_section()` bodies now interpolating `concise_timestamp_html()` alone | low | mitigate | That function is already this project's documented raw-markup-producing helper and already escapes both the `title` attribute and the visible text internally; the change removes a wrapper around it and adds none. Re-escaping it here would double-encode and print tags as visible text, which is why the existing D-09 comment beside both call sites forbids it — that comment stays. |
| T-tsa-03 | Denial of Service | Accessibility regression from removing the Device/Pipeline status dots | medium | mitigate | The removed dots were colour-only signals with no accessible text of their own; the text they were adjacent to was a verbatim duplicate of the tile caption, which remains. Each signal's state is still carried by its own `stat-tile--ok/warn/error` modifier (top border plus tinted icon) driven from the same per-signal value, and `collect_anomalies()`/`_anomaly_banner_html()` still name every failing signal in text in the banner. Task 3's Check 3 pins the caption/value shape and Task 3's human-check point 6 requires the stale-device case be looked at on screen. |
| T-tsa-04 | Denial of Service | Accessibility regression from restyling and moving the battery readout | medium | mitigate | `role="status"` and the element id both survive unchanged, so `battery-trend.js`'s `getElementById` lookup and every Left/Right/Home/End reveal announcement keep working; `battery-trend.js` is not edited at all. The `min-height` reserve stays in `em` so it scales with the larger size, and the reveal text is fixed-width by construction, so the no-layout-jump guarantee holds with the chart now below rather than above. Task 3's Check 4 pins position, class list, live region, and the JS-side id reference together. |
| T-tsa-05 | Tampering | `layout.page_header()`'s emission reorder reaching three pages this task does not intend to change | low | mitigate | For a caller passing exactly one of the three optional blocks the concatenation is the identical string either way; Task 1's verify gate asserts the purpose-only output shape directly and runs all three companion page harnesses (`test_status_pages.py`, `test_config_page.py`, `test_view_pages.py`) before the task is done. |
| T-tsa-SC | Tampering | npm/pip/cargo installs | n/a | accept | No package-manager install of any kind. This task edits one stylesheet and three Python files, all stdlib-only, with no dependency change. |
</threat_model>

<verification>
1. `server/.venv/bin/python3 companion/test_status_pages.py` — all checks pass; the printed total equals the new `EXPECTED_CHECK_COUNT`, which is the real on-disk baseline plus exactly 5.
2. `server/.venv/bin/python3 companion/test_config_page.py` and `companion/test_view_pages.py` — both pass at their own unchanged `EXPECTED_CHECK_COUNT`s, proving `page_header()`'s reorder reached no other page.
3. `scripts/run-all-tests.sh` — exactly one harness in the FAILED list, `server/test_poll_loop.py` (known pre-existing digest mismatch). Coverage gate reports no new shortfall.
4. `git diff --stat` touches only `companion/layout.py`, `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`. `companion/static/battery-trend.js` is absent from the diff entirely.
5. `git diff companion/static/style.css` shows: `.section-intro` and `.section-intro > p` new next to `.section-caption`; `.stat-tile__value .mono` new immediately after `.stat-tile__value`; `.battery-readout` gained the Body size and the semibold weight and moved its margin from top to bottom. No other rule's declarations changed, and no new custom property, size, muted strength or `:has()` selector appears anywhere.
6. The live browser pass described in Task 3's `<human-check>` was performed against a real running `companion/app.py`, and its real observations — including anything that could not be exercised — are written into the SUMMARY.
</verification>

<success_criteria>
- The Health page renders a purpose sentence, two baseline-aligned section descriptions, two non-duplicating timestamp tiles with a visibly heavier value, a properly-spaced Screen grid, and a prominent readout above the chart.
- Every fix is built from this stylesheet's existing tokens and this codebase's existing class pairs; no new token, size, muted strength or component pattern is introduced.
- The sketch's 28px readout is translated to the Emphasis role rather than transplanted, and the reason (06.6.4 D-09's Display-role retirement) is written into the stylesheet where the next reader will find it.
- `role="status"`, the readout id, and `battery-trend.js` are all untouched, and the chart's keyboard reveal still works.
- Three existing checks are retargeted in place onto the signals that replaced the ones they measured; none is deleted.
- `EXPECTED_CHECK_COUNT` moved to the real on-disk baseline plus exactly 5, with the three retargets and the live-HTTP extension recorded as no-count-change edits.
- `scripts/run-all-tests.sh` shows only the pre-existing `server/test_poll_loop.py` failure.
- The three deliberately-untouched sketch differences (`.freshness-refresh`'s styling, `.page-header` as a flex row, the Corroboration tile's multi-row shape) are named in the SUMMARY with their reasoning, so the developer can overrule any of them knowingly.
</success_criteria>

<commits>
Focused and atomic, matching this session's established style (`git log --oneline -10`), referencing the quick task id rather than a phase-plan number:
- `feat(quick-260901-tsa): add the Health page purpose and both section descriptions`
- `fix(quick-260901-tsa): stop the Device and pipeline tiles printing their own label twice`
- `fix(quick-260901-tsa): grid-wrap the Screen tile and lift the battery readout above the chart`
- `test(quick-260901-tsa): pin the five Health sketch fixes, EXPECTED_CHECK_COUNT +5`
- `docs(quick-260901-tsa): record the Health sketch reconciliation`
</commits>

<output>
Create `.planning/quick/260901-tsa-fix-confirmed-visual-structural-gaps-bet/260901-tsa-SUMMARY.md` when done.
</output>
