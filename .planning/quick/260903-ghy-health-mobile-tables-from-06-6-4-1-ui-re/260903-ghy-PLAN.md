---
phase: quick-260903-ghy
plan: 260903-ghy
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - companion/pages/health_page.py
  - companion/static/style.css
  - companion/test_status_pages.py
autonomous: true
requirements: [QUICK-260903-ghy]

must_haves:
  truths:
    - "UIR-10 and UIR-11 are both closed by ONE new shared mechanism with TWO different content shapes — a `.data-cards` mobile list that replaces a `.data-table-wrap` below 960px, toggled by the same sibling-combinator idiom History's `.history-cards` already uses (06.6.3 D-07). The mechanism is shared; the per-table content mapping is decided separately for each table, because their column shapes genuinely differ."
    - "PER-TABLE DECISION, Resolution statistics (UIR-10) — horizontal scroll is REJECTED for this table, and the rejection is not a preference: `.data-table--prose { min-width: 0 }` exists precisely because 260901-uzi measured 1172px of content in an 831px container and ruled that a column of full sentences must WRAP, not scroll (see that rule's own comment in style.css). Re-answering UIR-10 with a scroll affordance would reinstate the exact defect 260901-uzi removed. The mobile shape is therefore stacked: Source label + Count on the primary line, the full Description as a full-width paragraph beneath it. This is also what the audit itself recommends at 06.6.4.1-UI-REVIEW.md's UIR-10 entry."
    - "PER-TABLE DECISION, Unresolved prefixes (UIR-11) — five columns of short comparison values (Prefix, Count, First seen, Last seen, Example callsign). A scroll affordance already ships here: quick task 260902-w4t's four-layer `background-attachment` scroll-edge shadow lands on EVERY `.data-table-wrap`, Health's in-card ones included (the `.page-section .data-table-wrap` `--color-dominant` cover override exists for exactly these three tables). So UIR-11's literal wording ('no scroll affordance') is already partly stale and MUST be re-measured before it is re-fixed. What is NOT fixed by that shadow is the reading task: First seen and Last seen are meant to be COMPARED, and a horizontal scroller that shows one of them at a time makes the comparison impossible at 375px. The mobile shape is therefore a card per prefix: Prefix + Count on the primary line, Last seen on the secondary line, First seen and Example callsign inside a `<details>` disclosure — History's own two-lines-at-rest card shape, so a 40-prefix registry does not become a 40-screen page."
    - "The w4t scroll-edge shadow is NOT removed, weakened, or re-scoped by this task. It remains the desktop/tablet safety net for every table, and it remains the only affordance on the battery-readings table (which this task does not touch at all). `companion/static/style.css`'s `.data-table-wrap` and `.page-section .data-table-wrap` declaration blocks carry zero diff."
    - "NEW CSS RULES ONLY — no existing selector list in style.css is edited. This is a hard constraint with a concrete cause found during planning: `companion/test_status_pages.py` pins three selectors by exact literal (`css_source.index('.data-table {')`, `css_source.index('.data-table--prose {')`, `css_source.index('.data-table td.desc {')`), so appending a second selector to any of those rules turns a passing harness check into a `ValueError` at read time. `.data-card__desc` therefore gets its OWN rule repeating the file's single 70% muted mix literal (`color-mix(in srgb, var(--color-text) 70%, transparent)`) rather than joining `.data-table td.desc`'s selector list. Repetition of that literal is already this file's established practice — `.section-caption`, `.data-table th`, `.filter-bar__count` and `.battery-readout__detail` all carry the same literal independently."
    - "NO NEW DESIGN TOKENS, NO NEW SIZES, NO NEW COLOURS. Every value in every new rule is either an existing `var(--…)` token or a literal already present elsewhere in style.css (the 70% muted mix, and `.data-table th`'s 11px / 0.06em / uppercase label tier, which `.data-card__label` mirrors so the card's field labels read at the same quiet tier the table header they replace does). `test_status_pages.py`'s existing file-wide guard forbidding `--color-text-muted` must keep passing untouched."
    - "NO NESTED CARD SURFACE. Both card lists render INSIDE a `.page-section` card (`health_page.py::render()` wraps the registry and the stats table in `<section class=\"page-section page-section--nested\">` each), so a `.history-card`-style `--color-dominant` fill with a border and a hover shadow would put a card on a card — the elevation vocabulary this project already walked back once (06.6.4 D-03, and quick task 260902-iag's own reversal on this same page). `.data-card` instead keeps the row-hairline rhythm of the table rows it replaces: padding, a `1px solid var(--color-border)` bottom hairline, and no hairline on the last item — mirroring `.data-table td`'s own `border-bottom` and `.data-table tbody tr:last-child td`'s clean bottom edge. No fill, no radius, no shadow, no hover state."
    - "BOTH REPRESENTATIONS COEXIST IN THE DOM, exactly as History's do — the toggle is CSS `display`, never DOM removal, because `companion/static/list-filter.js` re-queries `[data-filter-text]` on every input event specifically so both representations stay filterable across breakpoints (that file's own comment states this). The desktop `<table>` markup for both Health tables is UNCHANGED: `_registry_table_html()`'s output and `_stats_table_html()`'s `layout.data_table(..., desc_columns=(1,), prose=True)` call both stay byte-identical."
    - "FILTER PAIRING IS EXACT. Each registry card carries the same `data-filter-text` and the same `data-filter-group` integer as its paired `<tr>`. `list-filter.js` counts DISTINCT GROUPS, not elements, so 'N of N shown' must still read the true prefix count after the DOM element count doubles. The existing comment in `_registry_row_html()` ('this card has only one representation per row (no mobile-card pairing like History)') becomes false with this task and is corrected in place — it is prose, and leaving it would misdescribe the very pairing being added."
    - "NO SECOND DATA PASS. Both card builders consume the SAME `rows` list and the SAME `now` value their table builders consume; the registry card's timestamps come from the identical `layout.concise_timestamp_html(value, now, fallback=\"\")` call the `<tr>` makes (D-09 discipline). A harness check asserts the timestamp markup is byte-identical between the two representations for the same row, so they cannot drift into two formats."
    - "HEADER STRINGS ARE SINGLE-SOURCED. The card field labels are the table's own header words, not re-typed literals: `_STATS_HEADERS = (\"Source\", \"Description\", \"Count\")` and `_REGISTRY_HEADERS = (\"Prefix\", \"Count\", \"First seen\", \"Last seen\", \"Example callsign\")` become module constants, consumed by both the table builder and the card builder. `_stats_table_html()`'s `layout.data_table()` call and `_registry_table_html()`'s local `headers` tuple must produce byte-identical output after the promotion."
    - "NO CHROME WITH NO DATA — the standing rule on this page (`_registry_section()`'s docstring, `_stats_table_html()`'s empty-string return). An empty registry renders the `empty_state()` block and NO `.data-cards` list; `stats is _DB_UNAVAILABLE` or `stats[\"total\"] == 0` renders neither table nor cards. Both card builders return `\"\"` for an empty input list."
    - "EVERY COLUMN STAYS REACHABLE ON MOBILE. Stats: Source, Count and the FULL Description text (never truncated, never behind a disclosure — the description IS the content of that table). Registry: Prefix and Count at rest, Last seen at rest on the secondary line, First seen and Example callsign one tap away in the `<details>` disclosure. Nothing is dropped from either table on mobile."
    - "ANTICIPATED HARNESS COLLATERAL, found during planning: `_anomaly_detail_list_markup_is_gone` (companion/test_status_pages.py L1309-1324) asserts `rendered.count(\"<ul\") == 0` and `rendered.count(\"<li\") == 0` over the WHOLE rendered Health page. Its fixture happens to seed neither runway events nor unresolved prefixes, so it will most likely still pass by accident — that accident is exactly the fragility worth removing. Retarget it to the anomaly banner's own element slice so it asserts its real subject (the retired anomaly detail list) rather than a page-wide list ban that a legitimate card list would trip. Retarget in place, no count change, and record it in SUMMARY.md."
    - "The rest of the existing Health harness must pass UNMODIFIED. Specifically read during planning and expected to stay green untouched: `_prose_table_opts_out_alone` (counts `data-table--prose` exactly once, and pins the `.data-table` / `.data-table--prose` source order), `_desc_column_muted_end_to_end` (counts `'<td class=\"desc\">'` exactly `len(_SOURCE_ROWS)` times — the card's prose class is `data-card__desc`, which does NOT match that literal, chosen deliberately for this reason), and the `rendered.count('<span class=\"mono\" title=') < 2` check at L1117 (a floor, so additional timestamp spans are safe). If ANY of these three needs an edit, STOP and report it rather than editing it."
    - "`EXPECTED_CHECK_COUNT` in `companion/test_status_pages.py` moves 126 -> 130 (four new checks, none retired). The number is confirmed by RUNNING the harness and reading the reported total, never by arithmetic alone — the file's own count comment says it was last re-derived from the real on-disk `check()` total at merge time, and this task continues that practice."
    - "ZERO CROSS-PAGE LEAK. `companion/pages/history_page.py`, `companion/pages/airlines_page.py`, `companion/layout.py`, `companion/static/list-filter.js`, `companion/app.py` and everything under `server/` carry ZERO diff from this task. `layout.data_table()` is NOT extended with a card mode — the two Health tables have different content shapes, so a generic builder would need a per-table shaping callback, which is more coupling than two 20-line page-local builders. History's `.history-card*` rules and markup are untouched; the older page-scoped vocabulary and the new generic one coexist, with a comment in style.css stating that consolidation is deliberately deferred rather than forgotten."
    - "VERIFICATION IS A REAL BROWSER AT 375px, against a COPY of `/tmp/skypane-prod-state` (confirmed present on disk at planning time: `history.db` + `illustration_overrides`), never the original — `cp -R` into scratch first. That snapshot has NO `poll_state.json`, so the unresolved-prefix registry renders EMPTY from it as-is: the copy MUST be seeded with production-shaped prefixes via `poll_loop.save_poll_state(copy_dir, {\"unresolved_prefixes\": {...}})` (the same call `_seed_unresolved_prefixes()` makes) with first/last-seen timestamps days apart, or UIR-11 cannot be reproduced at all and the 'after' measurement would be vacuous. Verify the stats table has data in the copy too (it reads `runway_events` route_source counts over the last RESOLUTION_WINDOW_DAYS) and seed the copy if it does not."
    - "The BEFORE tree is reconstructible without anyone remembering a pre-edit capture: Task 1 records `BASE_SHA=$(git rev-parse HEAD)` as its first action and Task 3 rebuilds the before tree with `git archive $BASE_SHA`. Both trees are served against SEPARATE `cp -R` copies of the same seeded snapshot."
    - "Browser method, established by quick tasks 260903-c4o and 260903-etm on this repo and reused verbatim: if no MCP Playwright tool is reachable, launch the cached Playwright Chromium at `~/Library/Caches/ms-playwright/chromium-1228` with LEGACY `--headless` (NOT `--headless=new`, which c4o reproduced hanging indefinitely on `Page.captureScreenshot` in this environment) plus a fixed `--remote-debugging-port`, and drive it over raw CDP using Node's built-in WebSocket/fetch globals."
    - "Computed-style assertions ALONE are not sufficient sign-off. The project's own recorded lesson is that computed-style checks missed a real mobile nav bug; Task 3 therefore also captures 375px screenshots of both Health sections in both trees, exercises the disclosure and the filter for real, and SUMMARY.md flags the result for developer sign-off on a real phone (offer a cloudflared tunnel against the seeded copy, as quick task 260903-etm did) rather than declaring the visual result settled."
    - "This task stays ON THE CURRENT BRANCH `claude/health-mobile-tables-uir-10-11` (already forked cleanly from origin/main's tip including PR #36 and the Airlines-upload batch). No new branch, no re-fork."
  artifacts:
    - path: "companion/pages/health_page.py"
      provides: "Two mobile card-list builders (`_stats_cards_html()`, `_registry_cards_html()`) rendering as DOM siblings before their unchanged desktop tables, plus the two promoted header constants both representations read"
      contains: "_registry_cards_html"
    - path: "companion/static/style.css"
      provides: "The `.data-cards` / `.data-card` mobile representation and its 960px sibling-combinator toggle pair — new rules only, no edit to any existing selector list"
      contains: ".data-cards ~ .data-table-wrap"
    - path: "companion/test_status_pages.py"
      provides: "Four new checks pinning the stats card list's completeness, the registry card list's filter pairing and timestamp identity, the stylesheet toggle contract, and the no-chrome-with-no-data + no-cross-page-leak boundary; EXPECTED_CHECK_COUNT re-derived from a real run"
      contains: "EXPECTED_CHECK_COUNT"
  key_links:
    - "`.data-cards ~ .data-table-wrap` requires the card list to be a DOM sibling that PRECEDES its table inside the same parent `<section>`. `_registry_section()` returns `header + filter + cards + table` and `_stats_table_html()` returns `cards + table` — reordering either breaks the toggle silently, with both representations visible at once."
    - "`data-filter-group` is the link between a registry card and its `<tr>`: same integer, or `list-filter.js`'s 'N of N shown' doubles."
    - "`_STATS_HEADERS` / `_REGISTRY_HEADERS` are the link between each table's `<th>` text and its card's field labels — one tuple, two consumers, no re-typed strings."
    - "`layout.concise_timestamp_html(value, now, fallback=\"\")` is the link between the registry `<tr>` cell and the card field: identical call, identical arguments, byte-identical markup."
---

<objective>
Close UIR-10 and UIR-11 from `06.6.4.1-UI-REVIEW.md` — Health's two data tables are unusable at a
375px phone viewport (the Resolution-statistics Description column squeezed to 129px with a 171px-tall
first row; the Unresolved-prefixes table clipped mid-cell at "06:10 UTC (5d" with Last seen and Example
callsign off-screen).

Purpose: Health is the page whose entire job is answering "is everything fine?" at a glance. Two of its
three data surfaces currently cannot be read on the device most likely to be asking that question.

Output: A shared `.data-cards` mobile representation, shaped differently per table (stacked prose for
the stats table, a two-line card with a disclosure for the registry), both toggled against their
unchanged desktop tables at 960px; four new harness checks; and a real-browser 375px before/after
measurement set against a seeded copy of production-shaped state.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.claude/CLAUDE.md
@.planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-REVIEW.md
@companion/pages/health_page.py
@companion/pages/history_page.py
@companion/static/style.css
@companion/test_status_pages.py
@.planning/quick/260903-etm-history-render-gallery-remove-the-top-of/260903-etm-SUMMARY.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Shared .data-cards mechanism + Resolution-statistics mobile shape (UIR-10)</name>
  <files>companion/static/style.css, companion/pages/health_page.py, companion/test_status_pages.py</files>
  <behavior>
    - Rendering Health with real resolution stats emits, inside the Resolution-statistics section and
      BEFORE its `.data-table-wrap`, exactly one `<ul class="data-cards">` holding exactly
      `len(health_page._SOURCE_ROWS)` `<li class="data-card">` items.
    - Every source label, every count value and every FULL gloss sentence from `_SOURCE_ROWS` appears
      inside that list; no gloss is truncated or elided.
    - The desktop table is still emitted in the same render and still carries
      `class="data-table data-table--prose"` with exactly `len(_SOURCE_ROWS)` `<td class="desc">` cells.
    - With `stats["total"] == 0` (no runway events seeded) the section emits neither a table nor a
      `.data-cards` list.
    - style.css declares `.data-cards ~ .data-table-wrap { display: none }` at base width and, inside
      the existing `@media (min-width: 960px)` block, `.data-cards { display: none }` plus
      `.data-cards ~ .data-table-wrap { display: block }` — the inverse pair History's `.history-cards`
      rules already establish.
    - `.data-table-wrap`'s and `.page-section .data-table-wrap`'s declaration blocks (w4t's scroll-edge
      shadow layers) are unchanged, and `.data-table {`, `.data-table--prose {` and
      `.data-table td.desc {` still exist as those exact literal selector-plus-brace strings.
    - `.data-card__label`'s font-size and colour equal `.data-table th`'s, read from the file — the
      card's field labels sit in the same quiet tier as the table header they replace.
  </behavior>
  <action>
    Record `BASE_SHA=$(git rev-parse HEAD)` in the task notes as the FIRST action — Task 3 rebuilds the
    before tree from it.

    In `companion/static/style.css`, add a new rule block placed immediately after the existing
    `.history-card__details` rule (so the two card-list vocabularies read side by side), introducing
    ONLY new selectors — do not append a selector to any existing rule anywhere in the file, and do not
    touch any existing declaration. New selectors: `.data-cards` (list reset: `list-style: none;
    margin: 0; padding: 0`), `.data-cards ~ .data-table-wrap` (`display: none`), `.data-card`
    (`padding: var(--space-sm) 0; border-bottom: 1px solid var(--color-border)`), `.data-card:last-child`
    (`border-bottom: none`), `.data-card__primary` (flex row, `align-items: baseline`,
    `gap: var(--space-sm)`, `justify-content: space-between`), `.data-card__value`
    (`margin-left: auto`), `.data-card__label` (mirroring `.data-table th`'s label tier: the same
    `font-size: 11px`, `font-weight: var(--weight-semibold)`, `letter-spacing: 0.06em`,
    `text-transform: uppercase` and `color: color-mix(in srgb, var(--color-text) 70%, transparent)`
    values that rule already carries — copy the values, not the selector), `.data-card__secondary`
    (`margin-top: var(--space-xs)`, `display: flex`, `gap: var(--space-sm)`), `.data-card__desc`
    (`margin: var(--space-xs) 0 0` and the same 70% muted colour literal), and `.data-card__details`
    (`margin-top: var(--space-sm)`).

    Write the rule block's own comment to state four things: that this is the generic sibling of
    History's page-scoped `.history-card*` vocabulary and that consolidating the two is deliberately
    deferred, not forgotten; that these cards render inside a `.page-section` card so they carry a row
    hairline instead of a nested surface (naming 06.6.4 D-03 and the `.data-table td` /
    `.data-table tbody tr:last-child td` rhythm they inherit); that `.data-card__desc` repeats the file's
    single 70% muted literal rather than joining `.data-table td.desc`'s selector list, because the
    harness pins that rule by exact literal; and that w4t's scroll-edge shadow stays in force as the
    desktop safety net. Then add the two inverse rules inside the existing `@media (min-width: 960px)`
    block, directly after the `.history-cards ~ .data-table-wrap { display: block }` rule already there.

    In `companion/pages/health_page.py`, promote the stats headers to a module constant
    `_STATS_HEADERS = ("Source", "Description", "Count")`, placed beside `_SOURCE_ROWS`, and have
    `_stats_table_html()` pass `list(_STATS_HEADERS)` to `layout.data_table()` — the rendered table must
    stay byte-identical, prove it before moving on. Add `_stats_cards_html(rows)` taking the same
    `stats["rows"]` list `_stats_table_html()` already has: return `""` for an empty list; otherwise one
    `<li class="data-card">` per `(label, gloss, count)` triple containing a `.data-card__primary` div
    holding `<span class="cell-primary">` with the escaped label and a `.data-card__value` span holding
    `<span class="data-card__label">` with `escape_html(_STATS_HEADERS[2])` followed by the escaped
    count, then a `<p class="data-card__desc">` holding the escaped gloss. Wrap the items in
    `<ul class="data-cards">`. Every value goes through `escape_html()` — this module's single-escaping
    choke-point discipline, no exceptions. Then make `_stats_table_html()` return
    `_stats_cards_html(stats["rows"]) + <the existing table html>`, cards first (the sibling combinator
    depends on that order — say so in the docstring). Extend the docstring to record the per-table
    decision: why a scroll affordance is the wrong answer here specifically, citing
    `.data-table--prose`'s own measured 1172px-in-831px rationale.

    In `companion/test_status_pages.py`, add two checks. Check A ("the Resolution-statistics table has a
    complete mobile representation"): seed runway events across several `route_source` values, render,
    and assert exactly one `<ul class="data-cards">` in the page, exactly `len(_SOURCE_ROWS)`
    `<li class="data-card">` items, that the list's index is greater than
    `health_page.STATS_SECTION_HEADING`'s and LESS than the index of the `data-table--prose` table (card
    list precedes its table), that every `_SOURCE_ROWS` label and every full gloss string appears inside
    the card-list slice, that the count values match `resolution_stats()`'s own numbers, and that the
    desktop table is still present with its `desc` cells intact in the same render. Check B ("the mobile
    toggle contract and the rules it must not disturb"): read `style.css` once and assert the base
    `.data-cards ~ .data-table-wrap` hide rule and both `@media (min-width: 960px)` inverse rules exist
    with their expected declarations; assert `.data-card__label`'s `font-size` and `color` declarations
    are string-equal to `.data-table th`'s; assert `.data-table-wrap`'s declaration block still contains
    its `background-attachment` layer list; and assert the three literal selector strings the harness
    itself indexes by (`.data-table {`, `.data-table--prose {`, `.data-table td.desc {`) are all still
    present. Strip CSS comments before any presence/absence assertion so the check cannot be satisfied
    or defeated by comment prose.

    Update `EXPECTED_CHECK_COUNT` by running the harness and reading its reported total; append this
    task's contribution to the existing count comment in the file's established style.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py &amp;&amp; server/.venv/bin/ruff check . &amp;&amp; git diff --stat -- companion/pages/history_page.py companion/pages/airlines_page.py companion/layout.py companion/app.py companion/static/list-filter.js server/ | wc -l | grep -qx '0'</automated>
  </verify>
  <done>Health's Resolution-statistics section renders a complete `.data-cards` list before its unchanged `data-table--prose` table; the 960px toggle pair exists; no existing CSS selector list or declaration was edited; the Health harness is green at its new total with two added checks; the six out-of-scope files carry zero diff.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Unresolved-prefixes mobile shape with exact filter pairing (UIR-11)</name>
  <files>companion/pages/health_page.py, companion/test_status_pages.py</files>
  <behavior>
    - Rendering Health with N seeded unresolved prefixes emits exactly one
      `<ul class="data-cards">` in the Unresolved-prefixes section, holding exactly N
      `<li class="data-card">` items, positioned after the filter bar and before the registry
      `.data-table-wrap`.
    - The set of `(data-filter-text, data-filter-group)` pairs on the cards is exactly equal to the set
      on the registry `<tr>` elements — same text, same integers, no extras, no gaps.
    - The number of distinct `data-filter-group` values across the whole page equals N even though the
      element count carrying `data-filter-text` is 2N, so `list-filter.js`'s "N of N shown" stays true.
    - For each row, the `layout.concise_timestamp_html()` markup in the card is byte-identical to the
      markup in its paired `<tr>` for the same value.
    - Every registry column is reachable in the card: Prefix and Count on the primary line, Last seen on
      the secondary line, First seen and Example callsign inside a `<details class="data-card__details">`.
    - With an empty registry the section renders its `empty_state()` block and NO `.data-cards` list and
      NO filter bar (the standing no-chrome-with-no-data rule).
    - Health now renders exactly two `.data-cards` lists total (stats + registry) when both have data.
  </behavior>
  <action>
    In `companion/pages/health_page.py`, promote `_registry_table_html()`'s local `headers` tuple to a
    module constant `_REGISTRY_HEADERS = ("Prefix", "Count", "First seen", "Last seen",
    "Example callsign")` and have the table builder consume it — the rendered table must stay
    byte-identical, prove it before moving on.

    Add `_registry_cards_html(rows, now)` taking the SAME `rows` list and the SAME `now` value
    `_registry_table_html()` receives — never a second query, never a second `now`. Return `""` for an
    empty list. For each `(index, (prefix, count, first_seen, last_seen, example_callsign))`, emit
    `<li class="data-card" data-filter-text="…" data-filter-group="…">` carrying the identical
    lowercased-and-escaped filter text and the identical integer index its `<tr>` carries — extract that
    filter-text computation into one small shared helper used by BOTH builders so the two can never
    diverge. Card content: a `.data-card__primary` div with `<span class="cell-primary mono">` holding
    the escaped prefix and a `.data-card__value` span holding `<span class="data-card__label">` with
    `escape_html(_REGISTRY_HEADERS[1])` followed by the escaped count; a `.data-card__secondary` div
    with `<span class="data-card__label">` carrying `_REGISTRY_HEADERS[3]` followed by
    `layout.concise_timestamp_html(last_seen, now, fallback="")` interpolated VERBATIM (already-safe
    markup, never re-escaped); and a `<details class="data-card__details">` whose `<summary>` reads
    "More details" (History's own wording for the identical affordance) wrapping a `<dl>` with
    `_REGISTRY_HEADERS[2]` -> `concise_timestamp_html(first_seen, now, fallback="")` and
    `_REGISTRY_HEADERS[4]` -> `<dd class="mono">` with the escaped example callsign.

    Wire it in `_registry_section()`: return `header_html + filter_html + cards_html + table_html` —
    cards before the table, and state in the function's comment that the sibling-combinator toggle
    depends on that order. Correct `_registry_row_html()`'s now-false comment about having no mobile-card
    pairing: it now HAS one, and the `data-filter-group` integer is what pairs them — rewrite the comment
    to say that, naming `list-filter.js`'s distinct-group counting as the reason the integer must match.
    Extend `_registry_cards_html()`'s docstring with the per-table decision: five short comparison values
    where First seen and Last seen are meant to be read against each other, which a horizontal scroller
    at 375px makes impossible; and that w4t's scroll-edge shadow stays as the desktop safety net rather
    than being this table's mobile answer.

    In `companion/test_status_pages.py`, add two checks. Check C ("the registry's mobile representation
    is exactly paired with its table"): seed 3+ prefixes with first/last seen several days apart and
    distinct example callsigns; render; parse both the `<tr>` set and the `<li class="data-card">` set;
    assert equal counts, equal `(filter-text, filter-group)` sets, distinct-group count equal to the row
    count while the `data-filter-text` element count is exactly twice it; assert each card's
    `concise_timestamp_html` spans are byte-identical to its paired row's for the same value; assert the
    card list's index sits after the filter bar's and before the registry table wrap's; and assert every
    prefix, count, example callsign and both timestamps are reachable in the card slice. Check D ("no
    chrome with no data, and no cross-page leak"): with an empty registry assert zero `.data-cards`, zero
    `.data-card`, zero filter bar and the `empty_state()` block present in the Unresolved-prefixes
    section; with both tables populated assert exactly two `.data-cards` lists on the page; and assert
    `history_page.render()` and `airlines_page.render()` outputs contain zero occurrences of the new card
    class names, proving the mechanism did not leak onto a page that already has its own.

    Retarget `_anomaly_detail_list_markup_is_gone` (L1309-1324) in place: scope its zero-`<ul>`/`<li>`
    assertions to the anomaly banner element's own slice rather than the whole page, keeping its real
    subject and its description, adding and retiring no check. Record the retarget in SUMMARY.md.

    Re-derive `EXPECTED_CHECK_COUNT` by running the harness and reading its reported total.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 companion/test_status_pages.py &amp;&amp; server/.venv/bin/ruff check . &amp;&amp; git diff --stat -- companion/pages/history_page.py companion/pages/airlines_page.py companion/layout.py companion/app.py companion/static/list-filter.js server/ | wc -l | grep -qx '0'</automated>
  </verify>
  <done>The registry renders one card per prefix, exactly paired with its `<tr>` by filter text and group integer, with every column reachable and timestamps byte-identical across representations; empty registry renders no card chrome; History and Airlines carry neither the classes nor a diff; the Health harness is green at its final total.</done>
</task>

<task type="auto">
  <name>Task 3: Real-browser 375px before/after verification and full-suite green</name>
  <files>scripts/run-all-tests.sh (run only), companion/test_status_pages.py (count reconciliation only)</files>
  <action>
    Build the fixture first. `cp -R /tmp/skypane-prod-state` into scratch TWICE (one copy per tree) —
    never serve the original. The snapshot carries `history.db` and `illustration_overrides` but NO
    `poll_state.json`, so the registry would render empty and the UIR-11 measurement would be vacuous:
    seed BOTH copies identically with production-shaped unresolved prefixes via
    `poll_loop.save_poll_state(copy_dir, {"unresolved_prefixes": {...}})` — at least 6 prefixes, counts
    in the tens, `first_seen`/`last_seen` several days apart so the concise timestamps render in the
    "HH:MM UTC (Nd ago)" shape UIR-11 caught truncating, and realistic example callsigns. Check whether
    the copied `history.db` yields a non-empty Resolution-statistics table (it reads `runway_events`
    route_source counts over the last `RESOLUTION_WINDOW_DAYS`); if it does not, seed both copies with
    matching runway events too. Record exactly what was seeded in SUMMARY.md.

    Reconstruct the BEFORE tree with `git archive $BASE_SHA` (recorded in Task 1) into scratch and serve
    `companion/app.py --state-dir <before-copy>` from it; serve the current branch's code against
    `<after-copy>` on a second port. Drive a real browser at 375px and 1440px against both. If no MCP
    Playwright tool is reachable, use the established fallback: the cached Playwright Chromium at
    `~/Library/Caches/ms-playwright/chromium-1228` launched with LEGACY `--headless` and a fixed
    `--remote-debugging-port`, driven over raw CDP with Node's built-in WebSocket/fetch globals. Do not
    use `--headless=new` — it is a reproduced hang in this environment.

    Measure and record a BEFORE/AFTER table in SUMMARY.md covering, at 375px: the stats Description
    column's computed width and the first stats row's height in the BEFORE tree (expect ~129px / ~171px,
    matching the audit — if they do not match, say so rather than reporting the audit's numbers); the
    registry wrap's `scrollWidth` vs `clientWidth` in both trees; the AFTER tree's `.data-cards`
    visibility (`getComputedStyle(...).display` on each list, and `offsetParent !== null`) and its
    tables' `display: none`; every stats description paragraph's `scrollWidth <= clientWidth` AND its
    `textContent` string-equal to the full `_SOURCE_ROWS` gloss (proving no clipping and no truncation);
    the tallest stats item's height; and the Health page's total `scrollHeight` in both trees. At 1440px,
    assert in the AFTER tree that both `.data-cards` lists compute to `display: none`, both tables are
    visible, and the stats table's three column widths are unchanged from the BEFORE tree — the desktop
    no-regression gate.

    Exercise behaviour for real, not just styles: at 375px click a registry card's `<details>` summary
    and confirm First seen and Example callsign become visible with non-empty text; type a seeded prefix
    into the filter input and dispatch a real `input` event, then confirm the visible card count is 1 and
    the `[data-filter-count]` text reads "1 of N shown" with N equal to the seeded prefix count (not 2N —
    this is the group-pairing gate in a live browser). Capture 375px screenshots of both Health sections
    in both trees, plus one 1440px AFTER screenshot.

    Run `scripts/run-all-tests.sh` and record every harness's exact pass count and the coverage
    percentage; all 16 must be green and coverage must stay above `fail_under = 83`. Confirm
    `EXPECTED_CHECK_COUNT` matches the harness's actually-reported total one final time.

    In SUMMARY.md: record the measurement table, the seeding, the anomaly-check retarget, the per-table
    decision rationale for both tables, and flag the visual result for developer sign-off on a real
    phone — offer a cloudflared tunnel against the seeded AFTER copy, matching quick task 260903-etm's
    own closing step. Do not present the visual outcome as settled on computed styles alone.
  </action>
  <verify>
    <automated>scripts/run-all-tests.sh</automated>
    <human-check>Developer opens the tunnelled Health page on a real phone and confirms both tables are readable at their own device width: full description sentences on Resolution statistics, and every unresolved prefix's last-seen visible at rest with first-seen/example-callsign one tap away.</human-check>
  </verify>
  <done>All 16 harnesses green with exact counts and coverage recorded; a real browser at 375px shows both card lists rendering with their tables hidden, full untruncated descriptions, a working disclosure and a correctly-counted filter; 1440px shows the tables unchanged and the card lists hidden; the before/after measurement table and the real-phone sign-off request are in SUMMARY.md.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → companion HTTP service | Session-gated; `/health` is server-rendered from local state |
| ADS-B/adsbdb-sourced values → Health markup | Unresolved-prefix keys, counts and example callsigns originate upstream and are the only externally-influenced strings this task newly interpolates |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-ghy-01 | Tampering (XSS) | New card markup duplicating registry values into a second DOM representation | medium | mitigate | Every card value goes through `layout.escape_html()`, the module's single choke point; the only verbatim interpolations are `layout.concise_timestamp_html()`'s already-safe output, the identical call the `<tr>` makes. Check C asserts the two representations' timestamp markup is byte-identical, so a raw-string shortcut in one of them is visible as a diff |
| T-ghy-02 | Tampering (XSS) | `data-filter-text` on the new `<li>` elements | medium | mitigate | The attribute value is produced by the same shared helper both builders call, escaped before interpolation exactly as `_registry_row_html()` already does; Check C asserts the card and row attribute sets are equal, so an unescaped variant cannot pass |
| T-ghy-03 | Denial of service (readability) | The fix could hide data instead of restoring it | high | mitigate | Every column stays reachable by contract; Check A asserts full gloss strings, Check C asserts all five registry values; Task 3 asserts in a live browser that description text is neither clipped nor truncated and that the disclosure really opens |
| T-ghy-04 | Tampering (regression) | Editing an existing CSS selector list would break harness checks that index rules by exact literal | medium | mitigate | New rules only; Check B asserts the three pinned literal selectors still exist and that `.data-table-wrap`'s scroll-shadow layers are intact |
| T-ghy-05 | Repudiation | "N of N shown" silently doubling once every row has two DOM elements | low | mitigate | Group integers are paired by construction; Check C asserts distinct-group count equals row count while element count is 2N; Task 3 re-confirms it in a live filter interaction |
| T-ghy-SC | Tampering | npm/pip/cargo installs | n/a | accept | This task installs nothing — no package-manager step exists in any of its three tasks, so no legitimacy gate applies |
</threat_model>

<verification>
- `server/.venv/bin/ruff check .` clean (blocking CI step).
- `scripts/run-all-tests.sh`: all 16 harnesses green, `companion/test_status_pages.py` at its
  re-derived total (126 + 4 expected), every other harness at its prior count, coverage above
  `fail_under = 83`.
- `companion/pages/history_page.py`, `companion/pages/airlines_page.py`, `companion/layout.py`,
  `companion/app.py`, `companion/static/list-filter.js` and all of `server/` carry zero diff.
- style.css: no existing selector list or declaration edited; w4t's scroll-edge shadow intact;
  no new token, size or colour value introduced.
- Real browser at 375px against a seeded copy of production-shaped state: both card lists visible with
  their tables hidden, full untruncated descriptions, a working `<details>`, a correctly-counted filter;
  at 1440px, card lists hidden and the desktop tables measurably unchanged versus the BEFORE tree.
</verification>

<success_criteria>
- UIR-10 closed: the Resolution-statistics Description column is no longer a 129px column — at 375px the
  description renders as full-width prose beneath its source label and count, with every sentence
  complete.
- UIR-11 closed: no unresolved-prefix value is clipped mid-word at 375px; Prefix, Count and Last seen
  read at rest, First seen and Example callsign one tap away, with the desktop table and w4t's scroll
  shadow untouched behind the breakpoint.
- One shared mechanism, two per-table content shapes, each with its rejection of the alternative written
  into the source it governs.
- Four new harness checks; `EXPECTED_CHECK_COUNT` re-derived from a real run, not arithmetic; the
  anomaly-list check retargeted rather than left fragile.
- Measurements from a real browser at 375px and 1440px, before and after, recorded in SUMMARY.md, with
  the visual outcome flagged for real-phone developer sign-off rather than declared settled.
- Commits scoped `quick-260903-ghy` on `claude/health-mobile-tables-uir-10-11`; no new branch.
</success_criteria>

<output>
Create `.planning/quick/260903-ghy-health-mobile-tables-from-06-6-4-1-ui-re/260903-ghy-SUMMARY.md` when done
</output>
