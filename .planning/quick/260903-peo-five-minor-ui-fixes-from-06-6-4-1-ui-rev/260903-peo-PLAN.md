---
phase: quick-260903-peo
plan: 260903-peo
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - companion/app.py
  - companion/layout.py
  - companion/pages/health_page.py
  - companion/static/flash-cleanup.js
  - companion/static/style.css
  - companion/test_companion_app.py
  - companion/test_config_page.py
  - companion/test_status_pages.py
  - companion/test_view_pages.py
autonomous: false
requirements: [QUICK-260903-peo]

must_haves:
  truths:
    - "FIVE INDEPENDENT FINDINGS, FOUR FILE AREAS, ONE BRANCH. UIR-16 (404 page) touches companion/app.py only. UIR-14 + UIR-18 (Health) touch companion/pages/health_page.py + companion/static/style.css. UIR-17 (History) touches companion/static/style.css only. UIR-19 (Settings) adds companion/static/flash-cleanup.js plus its route/src/script-tag wiring. Grouping UIR-14 and UIR-18 into one task is deliberate: both edit health_page.py::render()'s freshness/tile region and both land their harness checks in companion/test_status_pages.py, so one task means ONE EXPECTED_CHECK_COUNT re-derivation for that file instead of two."
    - "UIR-16 — THE 404 PAGE MUST NOT LEAK HEALTH STATE TO UNAUTHENTICATED CLIENTS. Found during planning and load-bearing: `_not_found_page()` has ELEVEN call sites, and TWO of them are PRE-AUTH — `_serve_stylesheet()` (companion/app.py L776) and `_serve_script_file()` (L806), both reached before any `require_session()` gate because D-02 exempts static assets. Threading `health_severity` unconditionally would paint a warn/error nav dot for an unauthenticated caller. The fix is `self._is_authenticated()` (the existing pure predicate at companion/app.py L549 — it returns a bool and does NOT redirect, unlike `require_session()`): compute severity only on that branch, pass `None` otherwise. Do NOT add a `health_alert` parameter threaded through all eleven call sites; do NOT call `require_session()` from inside `_not_found_page()` (it emits a redirect as a side effect)."
    - "UIR-16 — DO NOT CALL `self.page_context()` FROM `_not_found_page()`. `page_context()` performs six-plus SQLite reads plus a device-config load and a gallery/runway filesystem scan per call. A 404 needs exactly one value. Use `health_page.safe_health_state(self.args.state_dir, history_db.utc_now_iso())` and read its `\"severity\"` key with the same `if health_state else \"ok\"` fallback `page_context()` itself uses at L705 — `safe_health_state()` is contractually never-raising, which is precisely why it is safe on an error path."
    - "UIR-16 — THE HEADING BECOMES `layout.page_header(\"Page not found\", purpose=...)`. That is the 30px serif `.page-title` role every other authenticated page opens with (06.6.2 D-15); the current bare `<h1 class=\"text-heading\">` is the 20px SECTION-heading role and is the actual defect. `purpose` is a one-sentence explanation, escaped by `page_header()` itself — pass a plain string, never pre-escaped markup. The existing 'Back to Settings' link paragraph is kept."
    - "UIR-14 — `align-items: stretch` IS NOT TOUCHED. The `.dashboard-grid` cross-axis declaration is a DELIBERATE REVERSAL by quick task 260901-uzi of 06.6.3's UXA-06 choice, made after the developer measured the live result (Pipeline 107.7px, Corroboration 261.8px, Resolution-rate 140.4px in one row) and asked for the opposite; the declaration is kept explicit rather than deleted specifically so the reversal shows in a diff, AND it is pinned by a stylesheet guard in companion/test_status_pages.py. Switching it to `align-items: start` would undo a decision that fixed a real problem AND break a harness check. UIR-14 is therefore closed by the SECOND option the audit itself offers: give the pipeline tile a second content line."
    - "UIR-14 — THE SECOND LINE IS REAL DATA, NOT FILLER. `server/history_db.py` defines `META_LAST_DETECTION = \"last_detection\"` and `server/poll_loop.py` L550 writes it on every detection (`history_db.set_meta(conn, history_db.META_LAST_DETECTION, now_iso)`) — it is live production data, verified from source, not a hypothetical key. It is read through the SAME `history_db.get_meta(conn, ...)` accessor `pipeline_ts` already uses."
    - "UIR-14 — THE NEW READ JOINS THE ATOMIC SNAPSHOT, IT DOES NOT BECOME A SEVENTH INDEPENDENT QUERY. `health_page.py::_collect_inputs()` grew from five reads to six under quick task 260902-l0b for exactly this reason, and its docstring records the rule: a read feeding the same section builder from the same DB in the same request belongs in the one snapshot. `last_detection` feeds `_pipeline_section()`, which already consumes `pipeline_ts` from that snapshot. Add it there (six -> seven) and extend the docstring's own count sentence in place. This does NOT reopen D-11: the registry/stats reads in `render()` stay independent, untouched."
    - "UIR-14 — THE SECOND LINE REUSES AN EXISTING TYPE TIER. There is no `.stat-tile__detail` class in companion/static/style.css (confirmed: the only `stat-tile__*` members are `__caption`, `__icon`, `__value`). Do NOT invent one and do NOT add a new size or colour. Reuse an existing muted tier already in the file — read the candidates from source (`.text-label`, `.cell-secondary`, `.battery-readout__detail`) and pick the one whose shipped role is 'a quieter second line under a value'. The `.stat-tile__value` primary line keeps its exact current markup and its `concise_timestamp_html()` call."
    - "UIR-14 — DEGRADATION IS EXPLICIT. `_pipeline_section()`'s existing `_DB_UNAVAILABLE` early return is unchanged. When `last_detection` is absent or falsy (a fresh install that has never detected an aircraft), `concise_timestamp_html()` returns its escaped `fallback` string with NO markup — the second line must either render that fallback honestly or be omitted entirely; it must NEVER render an empty element or a dangling label. Choose one, and state which in the SUMMARY."
    - "UIR-18 — THE PILL IS KEPT, NOT REPLACED. Quick task 260902-chc's `data-refresh-pill` span, its `hidden` attribute, its `data-loaded-at` attribute and companion/static/freshness.js are ALL untouched by this task. `freshness.js` carries ZERO diff. The persistent cue is an ADDITION rendered beside the pill."
    - "UIR-18 — THE ADDITION MUST NOT REINTRODUCE THE 260902-ep7 ANONYMOUS-BLOCK-BOX GAP. Found during planning and non-obvious: `.page-header` is a plain block box, and 260902-ep7 (BUG 1) removed a measured 28px title-to-purpose gap that existed because an inline-level `<span class=\"refresh-pill\">` stranded between the block `<h1>` and the block `<p>` forced the renderer to generate an anonymous block box with its own 20px line box. The pill escapes that today ONLY because `.page-header .refresh-pill` is `position: absolute; top: 8px; right: 0`. Dropping a bare inline `<span>` next to it recreates the exact same stranded-inline condition. The fix: `freshness_html` emits ONE block-level wrapper element containing both the persistent note and the (unchanged, absolutely-positioned) pill, so `.page-header` sees a block child between two block children and generates no anonymous box. The pill's own `.page-header .refresh-pill` rule is a DESCENDANT selector and still matches through the wrapper — verify `.page-header` itself carries `position: relative` (its containing-block role is stated in its own comment) so the pill's `top: 8px; right: 0` offsets are unchanged."
    - "UIR-18 — THE NOTE IS SERVER-RENDERED FROM THE VALUE ALREADY IN HAND. `render()` already holds `now` (computed once per request by companion/app.py's `page_context()`) and already interpolates it into `data-loaded-at`. The note renders `layout.concise_timestamp_html(now, now)`, whose documented output is `<span class=\"mono\" title=\"{full ISO}\">{HH:MM} UTC ({relative})</span>` — already-safe markup, interpolated VERBATIM, never re-escaped (D-09). Do NOT add a client-side ticker to make the 'ago' count up: no new JS, no new timer, no second `data-loaded-at` consumer. The page regenerates itself every 45s, so a render-time value is honest for its whole life."
    - "UIR-18 — THE NOTE'S WORDING MUST NOT HARDCODE THE REFRESH INTERVAL unless it is pinned. `AUTO_REFRESH_INTERVAL_MS = 45000` lives in companion/static/freshness.js and is not importable from Python. If the note's copy names a cadence, the number MUST be a Python constant pinned against freshness.js's literal by a cross-file harness check — the codebase's own duplicated-not-imported idiom (`*_SCRIPT_ROUTE`/`*_SCRIPT_SRC`, the panel-lookup DOM literals). Preferred and simpler: word the note so it states liveness and the refresh TIME without restating the interval, and add no constant at all."
    - "UIR-17 — THE REVEAL MECHANISM IS `opacity`, AND `visibility: hidden` IS FORBIDDEN HERE. This is the whole accessibility crux: `visibility: hidden` removes an element from the tab order and the accessibility tree, so a copy button hidden that way could never receive focus, `:focus-within` could never fire, and the button would become permanently unreachable by keyboard — strictly worse than today's always-visible state, which is exactly the regression this plan's constraints forbid. `display: none` is forbidden for the same reason. Use `opacity: 0` at rest (element stays focusable, stays in the tab order, stays in the accessibility tree) plus `pointer-events: none` so an invisible control cannot be clicked, and restore both on `tr:hover` and `tr:focus-within`."
    - "UIR-17 — THE SELECTOR MUST NOT CATCH THE EYE BUTTON. Found during planning: `history_page.py::_view_panel_button_html()` renders `class=\"copy-btn\"` too — it deliberately reuses `.copy-btn`'s 22px-visual/44px-hit-area shape. A rule targeting `.copy-btn` inside the table would hide the View-panel trigger, which this finding requires to stay ALWAYS VISIBLE. The exact discriminator, verified from source: the two copy buttons carry `data-copy-value` (`_copy_button_html()` L528) and the View-panel button does not (it carries `data-view-panel-src`/`data-view-panel-caption`). Scope the rule with the `[data-copy-value]` attribute selector."
    - "UIR-17 — MOBILE IS UNTOUCHED. The rule lives inside the existing `@media (min-width: 960px)` block (companion/static/style.css L3343+), so the three copy buttons inside each `.history-card`'s `<details>` disclosure keep their current always-visible behaviour below the breakpoint, exactly as the finding requires. `.history-card*` rules and history_page.py's card markup carry ZERO diff. Health's and Airlines' own `.data-table-wrap` reuse is unaffected because neither renders any `[data-copy-value]` element."
    - "UIR-17 — THE 44px HIT AREA AND THE ACCESSIBLE NAME SURVIVE. `.copy-btn::before`'s `inset: -11px` synthesized 44x44 hit area, the `aria-label`, and the `data-copy-feedback` `role=\"status\"` sibling span are all untouched — this task adds an opacity/pointer-events pair and changes nothing else about the control. The sketch-findings skill's touch-target floor register records `.copy-btn` as 'relocated, not removed, no accessibility trade-off'; that entry must remain true after this task."
    - "UIR-17 — NO NEW TRANSITION TOKEN IS NEEDED. companion/static/style.css already carries a global `@media (prefers-reduced-motion: reduce)` override (L212) that every transition in the file inherits for free (D-19) — its own comment states that no later plan needs its own reduced-motion rule for a simple transition. A plain `opacity` transition is covered automatically; do NOT add a second reduced-motion block."
    - "UIR-17 — `.data-table tbody tr:hover`'s EXISTING 4% TINT RULE IS NOT EDITED. It stays exactly as shipped (06.6.4 D-07). The new reveal is its own separate rule, following the file's established practice of a dedicated rule rather than appending selectors to an existing block — companion/test_status_pages.py pins several selectors by exact `css_source.index('<literal> {')` lookup, so extending an existing selector list can turn a passing check into a `ValueError` at read time."
    - "UIR-19 — THE SERVER-SIDE PRG REDIRECT IS NOT TOUCHED. `POST /settings` still redirects to `%s?flash=%s` (companion/app.py L1301), `_resolve_flash_text()` still resolves it, `FLASH_ROLES` still maps it, and `layout.flash_banner()` still renders it. The ONLY addition is a client-side cleanup that runs AFTER the banner has rendered from that query param."
    - "UIR-19 — `location.pathname` IS SAFE TODAY, AND WHY IS VERIFIED NOT ASSUMED. `companion/app.py` reads exactly ONE query parameter across the whole module: `params.get(\"flash\", [None])[0]` at L660 (confirmed by grep — it is the only `params.get(` call in the file). The `?next=` parameter appears only on `/login`, which renders through `login_shell()`, not `page_shell()`, and therefore never carries a flash banner. So replacing the whole search string is lossless today. Guard the cleanup anyway on BOTH conditions — a rendered flash banner element IS present AND `location.search` mentions `flash` — so a future page that adds a second query param cannot have it silently discarded by a stale assumption."
    - "UIR-19 — A NEW STATIC SCRIPT FILE, NOT AN INLINE `<script>` AND NOT A BOLT-ON TO A SIBLING. An inline script would break the file's external-asset discipline. `dirty-state.js` is the wrong home (it is the Settings dirty-form tracker, is Settings-scoped, and carries a harness check asserting it contains no timer/network construct), and `freshness.js` is Health-scoped by its `data-refresh-pill` guard. The flash banner is emitted by `page_shell()` for EVERY authenticated page (`/airlines` has its own flash keys), so the cleanup belongs in its own page-agnostic file that no-ops via a guard clause — the exact convention all six existing scripts follow."
    - "UIR-19 — THE SEVEN WIRING TOUCH POINTS ARE MECHANICAL MIRRORS OF THE EXISTING SIX SCRIPTS, and every one is required: (1) `companion/static/flash-cleanup.js`; (2) `FLASH_CLEANUP_SCRIPT_ROUTE` in companion/app.py beside `PANEL_LOOKUP_SCRIPT_ROUTE` (L115); (3) the `_HERE/static/...` path constant beside `_PANEL_LOOKUP_JS_PATH` (L219); (4) a thin pre-auth serve delegate beside `_serve_panel_lookup_script()` (L856); (5) the pre-auth `if path == ...` dispatch branch in `do_GET()` beside the panel-lookup branch (L1127); (6) `FLASH_CLEANUP_SCRIPT_SRC` in companion/layout.py beside `PANEL_LOOKUP_SCRIPT_SRC` (L88); (7) a seventh `<script src=\"%s\" defer></script>` line plus its interpolation argument in `page_shell()` (L944-949 / L965-978)."
    - "UIR-19 — THE 'EXACTLY SIX SCRIPT TAGS' HARNESS CHECK MUST BE RETARGETED, NOT DELETED. companion/test_companion_app.py L1821-1828 asserts `head.count('<script src=') == 6`. It becomes seven. This is a RETARGET IN PLACE with NO check-count change. The paired cross-file route/src list at L1719-1722 gains the new pair. Both edits are required — a passing suite after only one of them means the other check is not doing its job."
    - "UIR-19 — THE NEW FILE OBEYS THE ES5-SAFE / FORBIDDEN-SINK DIALECT. No `let`/`const`/arrow functions/template literals/backticks — the project's no-build-step idiom, stated in every sibling script's header. Before writing, READ `companion/test_config_page.py`'s `_FORBIDDEN_SCRIPT_SINKS` tuple (L1084) and the nav-dropdown/panel-lookup banned-token lists in companion/test_companion_app.py (L1237-1255) and confirm `history.replaceState` and `location.search`/`location.pathname` are not among the banned constructs. `freshness.js` already ships `window.location.reload()` and passes, so navigation APIs are not blanket-banned — but confirm from source, do not infer."
    - "EXPECTED_CHECK_COUNT IS RE-DERIVED BY RUNNING EACH HARNESS, NEVER BY ARITHMETIC. Four harness files are touched and each has its own counter: companion/test_companion_app.py (currently 125), companion/test_status_pages.py (currently 130), companion/test_view_pages.py (currently 52), companion/test_config_page.py (currently 64). For each, run the harness, read the reported total, and set the constant to that number — then extend that file's own trailing count-provenance comment in the established style (`+ N (quick 260903-peo Task X: <what>)`). test_status_pages.py's own comment explicitly records this practice ('re-derived from the real on-disk check() count at merge time, not carried forward from either branch's own arithmetic')."
    - "REAL-BROWSER VERIFICATION IS MANDATORY AND EXERCISES ALL FIVE FIXES CONCRETELY. Computed-style assertions alone are NOT sufficient sign-off — this project's own recorded lesson is that computed-style checks missed a real mobile nav bug. Method, established verbatim by quick tasks 260903-c4o / 260903-etm / 260903-ghy on this repo: if no MCP Playwright tool is reachable, launch the cached Playwright Chromium at `~/Library/Caches/ms-playwright/chromium-1228` with LEGACY `--headless` (NOT `--headless=new`, which hangs indefinitely on `Page.captureScreenshot` in this environment) plus a fixed `--remote-debugging-port`, driven over raw CDP using Node's built-in WebSocket/fetch globals. Authenticate via a real `POST /login` (fetch) and hand the server-issued cookie to the browser via CDP `Network.setCookie` — a UI-driven form login is non-deterministic here (260903-ghy root-caused why)."
    - "VERIFICATION RUNS AGAINST A COPY OF `/tmp/skypane-prod-state`, NEVER THE ORIGINAL. `cp -R` into scratch first. UIR-14's second line needs a `last_detection` meta row in the copy — if the snapshot has none, seed it (`history_db.set_meta(conn, history_db.META_LAST_DETECTION, <iso>)`) or the 'after' measurement is vacuous. UIR-17 and UIR-19 need at least one History row and one real save round trip respectively."
    - "THE KEYBOARD CHECK FOR UIR-17 IS A HARD GATE, not an optional extra. In the real browser, with the pointer parked away from the table, Tab into a History row's copy button and assert its computed `opacity` is 1 and its computed `pointer-events` is not `none` at that moment. A passing hover check with a failing keyboard check means the fix has made accessibility WORSE and must be reverted, not shipped."
    - "THIS TASK STAYS ON THE CURRENT BRANCH `claude/health-404-history-minor-fixes-uir`, already forked cleanly from origin/main's tip (PR #36 and PR #37 included). No new branch, no re-fork, no rebase."
    - "ZERO SCOPE CREEP. `companion/static/freshness.js`, `companion/static/copy-button.js`, `companion/static/panel-lookup.js`, `companion/static/dirty-state.js`, `companion/pages/history_page.py`, `companion/pages/airlines_page.py`, `companion/pages/config_page.py`, `companion/auth.py` and everything under `server/` carry ZERO diff. The remaining open UI-review items (UIR-01/02 theme picker, UIR-20..26 typography/spacing) are explicitly OUT OF SCOPE."
  artifacts:
    - path: "companion/app.py"
      provides: "A 404 page that opens with the shared 30px serif page_header() and paints the Health nav dot for authenticated callers only, plus the flash-cleanup script's route constant, path constant, pre-auth serve delegate and dispatch branch"
      contains: "page_header(\"Page not found\""
    - path: "companion/pages/health_page.py"
      provides: "A pipeline tile with a real second content line sourced from META_LAST_DETECTION in the same atomic snapshot, and a persistent server-rendered liveness cue wrapped with (not replacing) the existing hidden refresh pill"
      contains: "META_LAST_DETECTION"
    - path: "companion/static/style.css"
      provides: "The pipeline tile's second-line tier reuse, the page-header freshness wrapper rule, and the desktop-only opacity/pointer-events reveal for History's [data-copy-value] buttons on tr:hover / tr:focus-within"
      contains: "[data-copy-value]"
    - path: "companion/static/flash-cleanup.js"
      provides: "The ES5-safe, guard-clause-gated client-side history.replaceState() cleanup that strips a consumed ?flash= param after its banner has rendered"
      contains: "replaceState"
    - path: "companion/layout.py"
      provides: "FLASH_CLEANUP_SCRIPT_SRC and its seventh deferred <script> tag in page_shell()"
      contains: "FLASH_CLEANUP_SCRIPT_SRC"
  key_links:
    - "companion/app.py::_not_found_page() -> self._is_authenticated() -> health_page.safe_health_state() -> layout.page_shell(health_alert=...) — the gate that keeps health state off the two PRE-AUTH 404 paths (_serve_stylesheet, _serve_script_file)"
    - "server/poll_loop.py writes history_db.META_LAST_DETECTION -> health_page._collect_inputs() reads it into the one atomic snapshot -> _pipeline_section() renders it as the tile's second line"
    - "health_page.render()'s freshness_html block wrapper -> layout.page_header(freshness_html=...) -> .page-header's block-child sequence, which is what keeps 260902-ep7's anonymous-block-box gap fix intact"
    - "history_page._copy_button_html()'s data-copy-value attribute -> style.css's @media (min-width: 960px) reveal selector -> tr:hover / tr:focus-within — the [data-copy-value] discriminator is the ONLY thing separating the two copy buttons from the identically-classed View-panel eye button"
    - "companion/app.py FLASH_CLEANUP_SCRIPT_ROUTE == companion/layout.py FLASH_CLEANUP_SCRIPT_SRC -> page_shell()'s seventh <script> tag -> test_companion_app.py's route/src pair list (L1719) and its script-tag count check (L1821)"
---

<objective>
Close five minor findings from `06.6.4.1-UI-REVIEW.md` — UIR-16 (404 page heading + missing Health nav dot), UIR-14 (Health's near-empty pipeline tile), UIR-18 (Health's invisible auto-refresh cue), UIR-17 (History's desktop row clutter), UIR-19 (Settings' replayable `?flash=saved`) — each with the minimum viable change, each verified in a real browser against production-shaped data, with all sixteen harnesses green.

Purpose: these are the last five *minor* items in the page-by-page visual review that have a concrete, agreed fix. Each is small on its own; together they remove the remaining "obviously unpolished" surface from four different pages.

Output: edits to `companion/app.py`, `companion/layout.py`, `companion/pages/health_page.py`, `companion/static/style.css`; one new `companion/static/flash-cleanup.js`; harness updates in four `companion/test_*.py` files.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./.claude/CLAUDE.md
@.planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-REVIEW.md

Project skill — read before touching `companion/static/style.css`:
`.claude/skills/sketch-findings-skypane/SKILL.md` and its
`references/control-density.md` (the touch-target floor register records
`.copy-btn` as "relocated, not removed, no accessibility trade-off" — that
entry must still be true after Task 3; and the `:not()`-scoping guidance
there is the file's stated correct way to add a hover state next to an
existing rule).

Source files (read the named regions, not the whole file):
@companion/app.py — L549 `_is_authenticated()`, L660-720 `page_context()` + `_not_found_page()`, L96-120 script route constants, L213-220 static JS path constants, L849-860 serve delegates, L1095-1135 + L1205-1220 `do_GET()` dispatch, L1290-1330 `do_POST()` settings flash redirect
@companion/layout.py — L72-90 `*_SCRIPT_SRC` constants, L851-980 `page_shell()`, L982-1000 `flash_banner()`, L531-567 `concise_timestamp_html()`, L1131-1193 `page_header()`
@companion/pages/health_page.py — L1404-1418 `_pipeline_section()`, L2200-2240 `_collect_inputs()`, L2280-2436 `render()`
@companion/pages/history_page.py — L350-384 `_view_panel_button_html()`, L518-533 `_copy_button_html()`, L647-699 `_history_table_html()`
@companion/static/style.css — L205-225 global reduced-motion override, L355-400 `.page-title`/`.page-header`, L1098-1190 `.refresh-pill` + `.page-header .refresh-pill`, L1464-1505 `.copy-btn`, L1838-1935 `.data-table*`, L2327-2500 `.stat-tile*`, L2735-2775 `.dashboard-grid`, L3343+ the `@media (min-width: 960px)` block
@companion/static/freshness.js — read only; ZERO diff this task
</context>

<tasks>

<task type="auto">
  <name>Task 1: UIR-16 — 404 page uses page_header() and shows the Health nav dot for authenticated callers</name>
  <files>companion/app.py, companion/test_companion_app.py</files>
  <action>
Record `BASE_SHA=$(git rev-parse HEAD)` first — Task 5's before/after browser comparison rebuilds the pre-edit tree from it.

Rewrite `_not_found_page()` (companion/app.py L712-719):

1. Replace the bare `<h1 class="text-heading">Page not found.</h1>` with `layout.page_header("Page not found", purpose=<one short sentence>)`. `page_header()` escapes both arguments itself — pass plain strings, never pre-escaped markup. Keep the existing `<p class="text-body"><a href="%s">Back to Settings</a></p>` paragraph after the header. Promote the title and purpose strings to module constants if the file's own convention for user-facing copy calls for it (check the neighbouring `LOGIN_EXPLANATION_TEXT` precedent).

2. Thread `health_alert` into the `layout.page_shell(...)` call, gated on authentication. `_not_found_page()` has eleven call sites and TWO are PRE-AUTH — `_serve_stylesheet()` (L776) and `_serve_script_file()` (L806), both reached before any session gate because D-02 exempts static assets. So compute the severity inside `_not_found_page()` on the `self._is_authenticated()` branch only (the pure bool predicate at L549 — NOT `require_session()`, which emits a redirect as a side effect), and pass `None` otherwise. Source the value from `health_page.safe_health_state(self.args.state_dir, history_db.utc_now_iso())`, reading `["severity"]` with the same `if health_state else "ok"` fallback `page_context()` uses at L705. Do NOT call `self.page_context()` here — it performs six-plus SQLite reads, a device-config load and a filesystem scan for one value, on an error path.

Write a comment at the gate stating plainly that the branch exists to keep health state off the two pre-auth 404 paths, naming them, so a future editor cannot "simplify" it away.

3. Add TWO checks to companion/test_companion_app.py:
   - An authenticated 404 (request an unrouted authenticated path) renders `<h1 class="page-title">` (never `<h1 class="text-heading">`) and, when the seeded state is warn/error, contains the health-dot markup `layout._health_alert_markup()` produces.
   - An UNAUTHENTICATED request to a 404-producing pre-auth path renders NO health-dot markup, even with warn/error state seeded. This is the leak guard and is the more important of the two.

4. Run `server/.venv/bin/python3 -m companion.test_companion_app` (or the file's own documented invocation), read the reported total, set `EXPECTED_CHECK_COUNT` to that exact number, and extend the file's trailing count-provenance comment with `+ 2 (quick 260903-peo Task 1: ...)`. Do not compute the number by arithmetic.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -m companion.test_companion_app; test $? -eq 0</automated>
  </verify>
  <done>The 404 page renders a `.page-title` serif heading with a purpose sentence and the Back-to-Settings link; an authenticated 404 shows the Health nav dot when state is warn/error; an unauthenticated pre-auth 404 shows no dot under the same state; test_companion_app.py passes at its re-derived EXPECTED_CHECK_COUNT.</done>
</task>

<task type="auto">
  <name>Task 2: UIR-14 + UIR-18 — Health's pipeline tile gains a real second line, and the page gains a persistent liveness cue</name>
  <files>companion/pages/health_page.py, companion/static/style.css, companion/test_status_pages.py</files>
  <action>
**UIR-14 — pipeline tile second line.** Do NOT touch `.dashboard-grid`'s `align-items: stretch`: it is quick task 260901-uzi's deliberate reversal of UXA-06, kept explicit so the reversal shows in a diff, and pinned by a stylesheet guard in test_status_pages.py. Close the finding with the audit's second option instead.

1. In `_collect_inputs()` (L2222-2236), add a seventh read: `history_db.get_meta(conn, history_db.META_LAST_DETECTION)`, wrapped in the same `_safe_query(state_dir, lambda conn: ...)` shape `pipeline_ts` uses. Extend the docstring's own "grew from five reads to six" sentence in place to record six -> seven and why (same section builder, same DB, same request — the rule that docstring already states). This does NOT reopen D-11; the registry/stats reads in `render()` stay independent and untouched.

2. Give `_pipeline_section()` the new value as a parameter and render a second line beneath the existing `<p class="stat-tile__value">`. The primary line's markup and its `layout.concise_timestamp_html(pipeline_ts, now)` call are UNCHANGED. The second line is `concise_timestamp_html()` output too (already-safe markup, interpolated verbatim, never re-escaped — D-09), prefixed by a short label naming what it is.

3. There is NO `.stat-tile__detail` class in style.css — the only `stat-tile__*` members are `__caption`, `__icon`, `__value`. Do not invent one, do not add a size or a colour. Read `.text-label`, `.cell-secondary` and `.battery-readout__detail` from source and reuse whichever already plays "a quieter second line under a value". If a new class is genuinely unavoidable, it must declare only layout (margin), reusing an existing tier class alongside it.

4. Handle the absent case explicitly: `_pipeline_section()`'s existing `_DB_UNAVAILABLE` early return is unchanged; when `last_detection` is falsy, `concise_timestamp_html()` returns its escaped bare-string fallback. Either render that fallback honestly or omit the second line entirely — never an empty element or a dangling label. State the choice in SUMMARY.md.

**UIR-18 — persistent liveness cue.** `companion/static/freshness.js` carries ZERO diff. The `data-refresh-pill` span, its `hidden` attribute and its `data-loaded-at` attribute are all preserved byte-for-byte; this is an addition beside the pill.

5. In `render()` (L2351-2353), wrap the existing pill span and a NEW persistent note inside ONE block-level element, and pass that wrapper as `freshness_html`. The wrapper is load-bearing, not decorative: `.page-header` is a plain block box, and 260902-ep7 (BUG 1) removed a measured 28px title-to-purpose gap caused by a stranded inline-level child forcing an anonymous block box. The pill escapes that today only because `.page-header .refresh-pill` is absolutely positioned. A bare inline note would recreate the exact condition. A single block wrapper keeps `.page-header`'s children all block-level. `.page-header .refresh-pill` is a descendant selector and still matches through the wrapper — confirm from source that `.page-header` itself carries `position: relative` so the pill's `top: 8px; right: 0` offsets are unchanged, and confirm the wrapper introduces no new positioned ancestor.

6. The note's content is `layout.concise_timestamp_html(now, now)` — `now` is already in hand, computed once per request by app.py's `page_context()` and already interpolated into `data-loaded-at`. Its output is already-safe markup; interpolate verbatim. Add NO client-side ticker, NO new timer, NO second `data-loaded-at` consumer. Word the note so it communicates liveness plus the refresh time WITHOUT restating the 45s interval — that number lives in freshness.js as `AUTO_REFRESH_INTERVAL_MS` and is not importable from Python, so naming it in Python would need a pinned cross-file constant for no user benefit.

7. Add a style.css rule for the wrapper (spacing only — it must not add a border, a fill or a shadow; this is a header line, not a card) and, if needed, the second-line class from step 3. Add new rules; do not append selectors to existing blocks — test_status_pages.py pins several selectors by exact `css_source.index('<literal> {')` lookup, so extending a selector list can turn a passing check into a `ValueError`.

8. Add THREE checks to companion/test_status_pages.py:
   - The pipeline tile renders two content lines, with the second sourced from a seeded `last_detection` meta row (seed it, assert its rendered timestamp markup is byte-identical to what `concise_timestamp_html()` returns for the same `(ts, now)` pair — so the two can never drift into two formats).
   - Health's header renders the persistent note AND still renders the unchanged hidden `data-refresh-pill`/`data-loaded-at` span, with the note and pill inside one block wrapper that is a direct child of `.page-header` (the anonymous-block-box guard — pin the structural contract, not just the presence of the text).
   - `.dashboard-grid`'s `align-items: stretch` is still present and unedited (extend the existing 260901-uzi guard's assertion in place if one already covers it; add a new check only if it does not).

9. Re-derive `EXPECTED_CHECK_COUNT` by RUNNING the harness and reading the reported total; extend the file's trailing provenance comment with `+ 3 (quick 260903-peo Task 2: ...)`. If any pre-existing check needs an edit beyond a documented in-place retarget, STOP and report it rather than editing it.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -m companion.test_status_pages; test $? -eq 0</automated>
  </verify>
  <done>The Health pipeline tile renders two lines (freshness timestamp + last-detection timestamp from META_LAST_DETECTION, read inside the one atomic snapshot); `.dashboard-grid`'s `align-items: stretch` is unedited; Health's header renders a persistent server-rendered liveness note beside the unchanged hidden refresh pill, both inside one block-level wrapper; freshness.js has zero diff; test_status_pages.py passes at its re-derived EXPECTED_CHECK_COUNT.</done>
</task>

<task type="auto">
  <name>Task 3: UIR-17 — History's desktop copy buttons reveal on row hover and focus-within, eye button stays visible</name>
  <files>companion/static/style.css, companion/test_view_pages.py</files>
  <action>
Read `.claude/skills/sketch-findings-skypane/references/control-density.md` first — the touch-target floor register records `.copy-btn` as "relocated, not removed, no accessibility trade-off", and that entry must still be true when this task ends.

CSS-only change. No Python, no JS: `companion/pages/history_page.py` and `companion/static/copy-button.js` carry ZERO diff.

1. Add ONE new rule pair inside the EXISTING `@media (min-width: 960px)` block (companion/static/style.css L3343+), scoped to History's desktop table:
   - At rest: `opacity: 0` plus `pointer-events: none` on `[data-copy-value]` copy buttons inside `.data-table` rows, with a short `opacity` transition.
   - Revealed: full opacity and restored pointer events on `.data-table tbody tr:hover` and `.data-table tbody tr:focus-within`.

2. `visibility: hidden` and `display: none` are FORBIDDEN here and the rule must carry a comment saying so and why: both remove the element from the tab order and the accessibility tree, so the button could never receive focus, `:focus-within` could never fire, and a keyboard-only user would lose the copy affordance entirely — strictly worse than today's always-visible state. `opacity: 0` keeps the element focusable, in the tab order and in the accessibility tree; `pointer-events: none` is what stops an invisible control from being clickable, and it is restored by the same reveal selectors.

3. The selector MUST use the `[data-copy-value]` attribute discriminator. `history_page.py::_view_panel_button_html()` (L375) renders `class="copy-btn"` too — it deliberately reuses `.copy-btn`'s 22px-visual/44px-hit-area shape — and carries `data-view-panel-src`/`data-view-panel-caption`, never `data-copy-value`. A bare `.copy-btn` selector would hide the eye/View-panel button, which this finding requires to stay always visible.

4. Do NOT edit `.data-table tbody tr:hover`'s existing 4% tint rule (L1927) or `.copy-btn`'s base rule (L1464) — new rules only, for the `css_source.index()` reason above. Add NO `prefers-reduced-motion` block: the global override at L212 already covers every transition in the file for free (D-19), and its own comment says later plans must not add their own.

5. Mobile is untouched by construction (the rule lives inside the 960px block), so the three copy buttons inside each `.history-card`'s `<details>` disclosure keep today's always-visible behaviour. Health's and Airlines' `.data-table-wrap` reuse is unaffected because neither renders any `[data-copy-value]` element — state that verified fact in the rule's comment.

6. Add TWO checks to companion/test_view_pages.py:
   - A stylesheet contract check: the reveal rule exists inside the `min-width: 960px` block, targets `[data-copy-value]`, uses `opacity` (asserting the source contains NO `visibility: hidden` or `display: none` in this rule's own declaration block), and names both `tr:hover` and `tr:focus-within`.
   - A markup contract check: History's rendered desktop `<tr>` still carries both copy buttons WITH their `aria-label`s and their `data-copy-feedback` sibling spans, and the View-panel button in the same row carries `data-view-panel-src` and NOT `data-copy-value` — the cross-file guard that the discriminator this rule depends on cannot silently disappear.

7. Re-derive `EXPECTED_CHECK_COUNT` by RUNNING the harness; extend the file's trailing provenance comment with `+ 2 (quick 260903-peo Task 3: ...)`.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -m companion.test_view_pages; test $? -eq 0</automated>
  </verify>
  <done>Desktop History rows hide their two copy buttons at rest via opacity (never visibility/display) and reveal them on `tr:hover` and `tr:focus-within`; the eye/View-panel button is unaffected; mobile cards are unaffected; `aria-label`s, the 44px `::before` hit area and the feedback spans are untouched; test_view_pages.py passes at its re-derived EXPECTED_CHECK_COUNT.</done>
</task>

<task type="auto">
  <name>Task 4: UIR-19 — a consumed ?flash= param is stripped client-side after its banner renders</name>
  <files>companion/static/flash-cleanup.js, companion/app.py, companion/layout.py, companion/test_companion_app.py, companion/test_config_page.py</files>
  <action>
The server-side PRG redirect is NOT touched: `POST /settings` still redirects to `%s?flash=%s` (app.py L1301), `_resolve_flash_text()` still resolves it, `FLASH_ROLES` still maps it, `layout.flash_banner()` still renders it. This adds only a client-side cleanup that runs after the banner has rendered.

Before writing any JS, READ `companion/test_config_page.py`'s `_FORBIDDEN_SCRIPT_SINKS` tuple (L1084) and the banned-token lists in `companion/test_companion_app.py` (L1237-1255), and confirm `history.replaceState`, `location.search` and `location.pathname` are not among the banned constructs. `freshness.js` already ships `window.location.reload()` and passes, so navigation APIs are not blanket-banned — but confirm from source rather than inferring.

1. Create `companion/static/flash-cleanup.js` in the project's no-build-step ES5-safe subset (no `let`/`const`/arrow functions/template literals/backticks), wrapped in an IIFE with `"use strict"`, following the header-comment style every sibling script uses. Behaviour:
   - Guard clause first, in the established "served every page, no-ops via guard" convention: return immediately unless BOTH a rendered flash banner element is present in the DOM AND `location.search` mentions `flash`. Two conditions, not one — the banner check proves the param was actually consumed, and the search check proves there is something to clean.
   - Then `history.replaceState(null, "", location.pathname)`.
   - Document the blast radius in the header, with the verified reason it is lossless today: `companion/app.py` reads exactly ONE query parameter across the whole module (`params.get("flash", ...)` at L660 — the only `params.get(` call in the file), and `?next=` appears only on `/login`, which renders through `login_shell()`, never `page_shell()`, so it never carries a flash banner. State plainly that the two-condition guard is what stops a future second query param being silently discarded.
   - Use whatever selector the flash banner actually renders with — read it from `layout.flash_banner()` (L985-1000). If the banner has no stable hook beyond its class, either key on that class or add a data attribute to `flash_banner()`; if you add one, it becomes a cross-file DOM contract and needs the same duplicated-literal harness guard nav-dropdown.js and panel-lookup.js have.

2. Wire it through all SEVEN existing touch points, each a mechanical mirror of `panel-lookup.js`:
   - `FLASH_CLEANUP_SCRIPT_ROUTE` in companion/app.py beside `PANEL_LOOKUP_SCRIPT_ROUTE` (L115)
   - the `_HERE/static/...` path constant beside `_PANEL_LOOKUP_JS_PATH` (L219)
   - a thin pre-auth serve delegate beside `_serve_panel_lookup_script()` (L856)
   - the pre-auth `if path == ...` dispatch branch in `do_GET()` beside the panel-lookup branch (L1127)
   - `FLASH_CLEANUP_SCRIPT_SRC` in companion/layout.py beside `PANEL_LOOKUP_SCRIPT_SRC` (L88)
   - a seventh `<script src="%s" defer></script>` line in `page_shell()` (L944-949)
   - its interpolation argument in the same call's tuple (L965-978), with the same "unconditional, no-ops via guard clause" comment the sixth script carries

3. Update companion/test_companion_app.py — RETARGET IN PLACE, NO check-count change from either:
   - L1821-1828: `head.count('<script src=') == 6` becomes `== 7`, and add the deferred-tag assertion for the new SRC constant alongside the existing panel-lookup one.
   - L1719-1722: add the `(app_module.FLASH_CLEANUP_SCRIPT_ROUTE, layout.FLASH_CLEANUP_SCRIPT_SRC)` pair to the cross-file route/src list.
   Both edits are required — a green suite after only one means the other check is not doing its job.

4. Add checks:
   - companion/test_companion_app.py: the new script is served pre-auth (unauthenticated GET returns 200 with JS content type), and its source contains none of the banned ES5-unsafe/forbidden-sink tokens — mirroring the existing four pre-auth static-script regression checks and the nav-dropdown dialect check.
   - companion/test_config_page.py: a `POST /settings` still redirects to `SETTINGS_ROUTE?flash=<key>` (the PRG pattern is intact and unchanged), and the rendered Settings page for that redirect target carries BOTH the flash banner AND the flash-cleanup script tag — the pairing that makes the cleanup reachable.

5. Re-derive `EXPECTED_CHECK_COUNT` for BOTH files by RUNNING each harness and reading its reported total (test_companion_app.py's total already moved in Task 1 — re-derive it again here, do not carry Task 1's number forward). Extend each file's trailing provenance comment with `+ N (quick 260903-peo Task 4: ...)`.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -m companion.test_companion_app && server/.venv/bin/python3 -m companion.test_config_page; test $? -eq 0</automated>
  </verify>
  <done>`companion/static/flash-cleanup.js` exists, is ES5-safe, no-ops unless both a flash banner and a `flash` search param are present, and calls `history.replaceState(null, "", location.pathname)`; it is served pre-auth at its own route, `page_shell()` emits seven deferred script tags, the route/src pair is pinned cross-file, the server-side PRG redirect is unchanged, and both harnesses pass at their re-derived EXPECTED_CHECK_COUNTs.</done>
</task>

<task type="auto">
  <name>Task 5: Full suite plus real-browser before/after verification of all five fixes</name>
  <files>(no source edits — verification only; scratch scripts under the session scratchpad)</files>
  <action>
1. Run the whole suite: `scripts/run-all-tests.sh`. All sixteen harnesses green, coverage threshold met, ruff clean. If a harness flakes (260903-ghy recorded a live-HTTP poll-cooldown timing check in test_companion_app.py flaking once), re-run clean and record both runs in SUMMARY.md rather than declaring it green from one pass.

2. Build the verification environment:
   - `cp -R /tmp/skypane-prod-state <scratch>/after-state` and a second copy for the before tree. NEVER serve the original.
   - Seed each copy with what the findings need: a `last_detection` meta row (`history_db.set_meta(conn, history_db.META_LAST_DETECTION, <iso a few minutes old>)`) so UIR-14's second line has real content; at least one History row with a callsign AND a hex so both desktop copy buttons render; a `pipeline_ts` recent enough that Health is not in a fault state.
   - Rebuild the BEFORE tree with `git archive $BASE_SHA` (recorded in Task 1) into scratch, and serve both trees on separate ports against their own state copies.

3. Drive a real browser. If no MCP Playwright tool is reachable, use the established fallback (quick tasks 260903-c4o / 260903-etm / 260903-ghy): the cached Playwright Chromium at `~/Library/Caches/ms-playwright/chromium-1228`, launched with LEGACY `--headless` (NOT `--headless=new` — it hangs indefinitely on `Page.captureScreenshot` in this environment, reproduced twice) and a fixed `--remote-debugging-port`, driven over raw CDP with Node's built-in WebSocket/fetch globals. Authenticate each server via a real `POST /login` (fetch) and hand the server-issued cookie to the browser via CDP `Network.setCookie` — a UI-driven form login is non-deterministic across two same-password ports (260903-ghy root-caused why).

4. Exercise each fix concretely, before and after, and record measured values in a table in SUMMARY.md:
   - **UIR-16:** request an unrouted authenticated path. Assert the `<h1>` computed `font-family` is the serif stack and its `font-size` is the page-title size (30px), matching a real page's `<h1>` measured in the same run. Assert the Health nav dot element is present when state is seeded warn/error. Then repeat UNAUTHENTICATED against a pre-auth 404 path and assert NO dot markup is present — the leak guard, measured in the browser, not only in the harness.
   - **UIR-14:** measure the pipeline tile's `getBoundingClientRect().height` and the height of its rendered content, before and after, in the same Server & data grid row. The after tile must contain two visible text lines and materially less empty space; the Corroboration tile's own height must be unchanged. Screenshot the row.
   - **UIR-18:** assert the persistent note is visible (`opacity` 1, non-zero rect, non-empty text) on load with NO interaction and NO wait, and that the `data-refresh-pill` span is still present and still `hidden`. Also assert the `.page-header` title-to-purpose geometry did not regress into 260902-ep7's gap: measure the `<h1>` bottom edge to the purpose paragraph's top edge and compare against the same measurement on a page with no freshness block (Airlines), accounting for the note's own intentional line.
   - **UIR-17:** with the pointer parked away from the table, assert a row's `[data-copy-value]` buttons compute `opacity: 0`; hover the row and assert `opacity: 1` and `pointer-events` not `none`; assert the same row's `[data-view-panel-src]` button computes `opacity: 1` in BOTH states. Then the HARD GATE: move the pointer away, Tab into the row until a copy button is `document.activeElement`, and assert at that moment its computed `opacity` is 1 and its `pointer-events` is not `none`. A passing hover check with a failing keyboard check means the fix made accessibility worse — revert rather than ship. Also verify at 375px that the mobile card disclosure still shows all three buttons.
   - **UIR-19:** perform a real save on Settings, follow the redirect, assert the flash banner rendered AND `location.search` is empty afterwards; then reload and assert NO flash banner appears. Also assert the server still issued a genuine `302` to `?flash=saved` (read it off the network events) — the PRG pattern must be observably intact, not bypassed.

5. Capture screenshots at 1440px and 375px in both themes for the Health header/tile row and the History table, before and after.

6. Record in SUMMARY.md: the measurement table, the exact browser method used, every `EXPECTED_CHECK_COUNT` before/after value per file, and an explicit note that computed-style assertions alone are not sufficient sign-off — flag the visual result for developer confirmation on a real device, offering a cloudflared tunnel against the seeded copy (as 260903-etm did), with the exact commands for the developer to run.
  </action>
  <verify>
    <automated>scripts/run-all-tests.sh; test $? -eq 0</automated>
  </verify>
  <done>All sixteen harnesses green (with any flake re-run clean and both runs recorded), and a real-browser before/after measurement table in SUMMARY.md covering all five findings including the UIR-17 keyboard-focus hard gate and the UIR-16 unauthenticated no-dot check, with screenshots captured.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
Five minor UI fixes from `06.6.4.1-UI-REVIEW.md`, each verified in a headless real browser against a seeded copy of production-shaped state:
- UIR-16: the 404 page now opens with the standard 30px serif `page_header()` and shows the Health nav dot — for authenticated callers only.
- UIR-14: Health's "ADS-B pipeline last ran" tile gained a second line (last detection time, from `META_LAST_DETECTION`); `align-items: stretch` was deliberately left alone.
- UIR-18: Health gained a persistent server-rendered liveness cue beside the title; the "Updating…" pill and `freshness.js` are untouched.
- UIR-17: History's desktop copy buttons now reveal on row hover/focus-within (opacity, not visibility); the eye button stays visible; mobile is unchanged.
- UIR-19: a consumed `?flash=` param is stripped client-side after its banner renders; the server-side PRG redirect is unchanged.
  </what-built>
  <how-to-verify>
The headless checks and screenshots are in SUMMARY.md, but this project's own recorded lesson is that computed-style checks alone once missed a real mobile nav bug. Please confirm on a real device:

1. Start the companion against the seeded scratch copy (exact command in SUMMARY.md — never the original `/tmp/skypane-prod-state`).
2. Visit any bad URL (e.g. `/nope`). The heading should read as the same large serif title every other page uses, and if Health is warn/error the nav dot should be there. Sign out and try a bad URL again — no dot should appear.
3. On Health: the "ADS-B pipeline last ran" tile should no longer read as mostly empty, and a small "live / refreshed at …" cue should sit near the page title on load, without waiting.
4. On History (desktop width): the two copy buttons per row should be invisible until you hover the row. Then, WITHOUT touching the mouse, Tab through a row — each copy button must become visible when it receives focus. On a phone, the card disclosure should still show all three buttons.
5. On Settings: save something. You should see "Saved —" and a clean URL with no `?flash=saved`. Reload — the banner must NOT come back.

A cloudflared tunnel command for phone testing is in SUMMARY.md if useful.
  </how-to-verify>
  <resume-signal>Type "approved" or describe what looks wrong (with the page, the viewport width, and the theme).</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| unauthenticated browser -> companion HTTP handler | Pre-auth routes (`/static/style.css`, the seven `/static/*.js` routes, `/login`) answer before any session gate; everything else is behind `require_session()` |
| authenticated browser -> rendered page markup | Server-side row/meta values reach the DOM through `escape_html()` / the documented already-safe-markup contract |
| browser JS -> browser History API | `flash-cleanup.js` rewrites the address bar entry for the current document |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-peo-01 | Information Disclosure | `_not_found_page()` reached via the PRE-AUTH `_serve_stylesheet()` (app.py L776) and `_serve_script_file()` (L806) paths | medium | mitigate | Gate the health-severity computation on `self._is_authenticated()` (the pure bool predicate at L549) and pass `health_alert=None` otherwise; Task 1 adds a harness check asserting an unauthenticated pre-auth 404 renders no dot markup under seeded warn/error state, and Task 5 re-verifies it in the browser |
| T-peo-02 | Denial of Service | `_not_found_page()` performing DB work on an error path | low | mitigate | Use the single never-raising `health_page.safe_health_state()` call, never `self.page_context()` (six-plus SQLite reads + device-config load + filesystem scan); the read is additionally skipped entirely for unauthenticated callers by T-peo-01's gate |
| T-peo-03 | Tampering | New static route `/static/flash-cleanup.js` serving a file from disk | low | mitigate | The serve delegate is a thin mirror of `_serve_panel_lookup_script()` — a fixed module-level `_HERE/static/...` path constant, no request-derived path component, so no traversal surface is introduced; Task 4 adds the same pre-auth-serving regression check the six sibling scripts carry |
| T-peo-04 | Tampering | `flash-cleanup.js` writing to the History API | low | mitigate | The replacement URL is `location.pathname` — a same-document value read from the browser, never a server- or attacker-supplied string, and never a URL assembled from DOM content; the file contains no URL-taking navigation form (matching freshness.js's own stated discipline) and is covered by the ES5/forbidden-sink token guard |
| T-peo-05 | Information Disclosure | `META_LAST_DETECTION` timestamp newly surfaced on the Health page | low | accept | Health is already fully authenticated and already surfaces `last_pipeline_run`, device-health timestamps and per-flight detection history; a detection timestamp is the same class of data at the same trust level, adding no new disclosure |
| T-peo-06 | Denial of Service | Seventh read added to `_collect_inputs()`'s per-request snapshot | low | accept | One additional `get_meta()` key lookup inside the existing single open connection, on a page already performing six such reads; the 260902-l0b precedent grew the snapshot five -> six on the same reasoning with no measured impact |
| T-peo-SC | Tampering | npm/pip/cargo installs | high | mitigate | Not applicable — this task installs no packages. No new dependency is added to `server/requirements*.txt`, `package.json` or any lockfile; `flash-cleanup.js` is hand-written in the project's existing no-build-step, no-dependency JS idiom |
</threat_model>

<verification>
- `scripts/run-all-tests.sh` green: all sixteen harnesses pass, coverage threshold met, ruff clean.
- Every touched harness's `EXPECTED_CHECK_COUNT` was set from that harness's own RUN-reported total, not from arithmetic, and each file's trailing provenance comment was extended in the established style.
- `git diff --stat` shows edits confined to: `companion/app.py`, `companion/layout.py`, `companion/pages/health_page.py`, `companion/static/style.css`, the new `companion/static/flash-cleanup.js`, and the four `companion/test_*.py` files. `companion/static/freshness.js`, `companion/pages/history_page.py`, `companion/pages/airlines_page.py`, `companion/pages/config_page.py`, `companion/auth.py` and everything under `server/` show ZERO diff.
- `.dashboard-grid`'s `align-items: stretch` declaration is byte-identical to before this task.
- No new design token, size or colour was introduced in `companion/static/style.css`; the file-wide `--color-text-muted` ban still passes.
- Real-browser before/after measurements recorded for all five findings, including the UIR-17 keyboard-focus hard gate and the UIR-16 unauthenticated no-dot check.
- Screenshots captured at 1440px and 375px in both themes.
</verification>

<success_criteria>
- UIR-16: an authenticated 404 renders `<h1 class="page-title">` with a purpose sentence and the Health nav dot; an unauthenticated pre-auth 404 renders neither the dot nor any health state.
- UIR-14: the pipeline tile renders two content lines sourced from the one atomic snapshot; `align-items: stretch` and the Corroboration tile's height are unchanged.
- UIR-18: a persistent liveness cue is visible on Health at load with no interaction and no wait; the hidden `data-refresh-pill` span and `freshness.js` are unchanged; `.page-header`'s title-to-purpose geometry has not regressed into 260902-ep7's anonymous-block-box gap.
- UIR-17: desktop copy buttons are `opacity: 0` at rest and revealed on `tr:hover` AND `tr:focus-within`; a Tab-focused copy button is visible and clickable; the eye button is always visible; mobile cards are unchanged; `aria-label`s and the 44px hit area survive.
- UIR-19: after a save, the flash banner renders and the URL carries no query string; a reload shows no banner; the server still issues a real `302` to `?flash=saved`.
- All sixteen harnesses green; the developer has signed off the visual result on a real device (or recorded the remaining sign-off as open in SUMMARY.md).
</success_criteria>

<output>
Create `.planning/quick/260903-peo-five-minor-ui-fixes-from-06-6-4-1-ui-rev/260903-peo-SUMMARY.md` when done.
</output>
