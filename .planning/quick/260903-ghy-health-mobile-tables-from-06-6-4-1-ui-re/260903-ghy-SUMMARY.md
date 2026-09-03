---
phase: quick-260903-ghy
plan: 260903-ghy
subsystem: ui
tags: [companion, health-page, responsive, mobile, css, python]

requires:
  - phase: 06.6.4.1
    provides: "Health's two migrated data tables (Resolution statistics, Unresolved prefixes) and History's .history-cards mobile-card precedent this task's .data-cards mechanism mirrors"
provides:
  - "A shared `.data-cards`/.data-card mobile representation, toggled against `.data-table-wrap` via the same sibling-combinator idiom History's `.history-cards` already uses"
  - "Resolution-statistics mobile shape (UIR-10): stacked prose — source label + count on the primary line, the full untruncated description beneath"
  - "Unresolved-prefixes mobile shape (UIR-11): a two-line card (Prefix+Count, Last seen) with First seen/Example callsign behind a `<details>` disclosure, exactly paired with its `<tr>` by `data-filter-text`/`data-filter-group`"
  - "Four new harness checks (128 -> 130 net across two tasks) plus one retarget of a fragile page-wide `<ul>`/`<li>` ban onto the anomaly banner's own element slice"
affects: [health-page-mobile, ui-review-06.6.4.1]

tech-stack:
  added: []
  patterns:
    - "Second page-scoped mobile-card vocabulary (`.data-card*`) coexisting deliberately unconsolidated with History's `.history-card*` — documented as a deferred consolidation, not an oversight"
    - "Shared filter-text helper (`_registry_filter_text()`) extracted so two DOM representations of the same row can never diverge on `data-filter-text`"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/test_status_pages.py

key-decisions:
  - "Resolution statistics (UIR-10) gets stacked prose, not a horizontal scroll affordance — `.data-table--prose`'s own comment already measured 1172px of content in an 831px container and ruled scroll wrong for this table specifically; re-answering with a scroller would reinstate that exact defect."
  - "Unresolved prefixes (UIR-11) gets a two-line card with a disclosure, not a horizontal scroll affordance — First seen and Last seen must be readable AGAINST each other, which a one-column-at-a-time scroller defeats; w4t's scroll-edge shadow stays as the desktop safety net only."
  - "No nested card surface — `.data-card` carries no fill/radius/shadow, only the row-hairline rhythm the `<td>` rows it replaces already had, because these cards render inside an existing `.page-section` card (avoiding the card-on-card elevation defect 06.6.4 D-03 already reversed once)."
  - "Auth for the real-browser verification was established via a real POST /login (curl/fetch), then handed to the browser as a CDP-injected cookie, after discovering that companion/auth.py's session token (HMAC(password, expiry), no port/host component) is valid across every port sharing the same password within the same expiry second — a UI-driven second login in the same browser profile was non-deterministic once the first had already set a cookie for the same host."

requirements-completed: [QUICK-260903-ghy]

coverage:
  - id: D1
    description: "UIR-10 closed — Resolution-statistics renders as full-width stacked prose (label, count, untruncated description) below 960px, with its unchanged desktop table hidden"
    requirement: "QUICK-260903-ghy"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_stats_cards_list_complete_and_precedes_table (Check A)"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py::_data_cards_toggle_contract_and_untouched_rules (Check B)"
        status: pass
      - kind: automated_ui
        ref: "raw-CDP measurement script, before/after @375px against a seeded production-shaped copy — 4/4 description paragraphs scrollWidth==clientWidth, text byte-equal to _SOURCE_ROWS glosses"
        status: pass
    human_judgment: true
    rationale: "This project's own recorded lesson (feedback_real_device_ui_verification) is that computed-style checks alone missed a real mobile nav bug once already; the plan itself requires flagging this visual outcome for real-phone developer sign-off rather than declaring it settled on automation alone."
  - id: D2
    description: "UIR-11 closed — Unresolved prefixes renders as a card per row (Prefix+Count+Last seen at rest, First seen/Example callsign in a disclosure) below 960px, exactly paired with its table row by filter text/group"
    requirement: "QUICK-260903-ghy"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py::_registry_mobile_cards_paired_with_table (Check C)"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py::_no_chrome_with_no_data_and_no_cross_page_leak (Check D)"
        status: pass
      - kind: automated_ui
        ref: "raw-CDP interaction exercise — <details> opened with non-empty text; filter on a seeded prefix returned '1 of 6 shown' (N, not 2N)"
        status: pass
    human_judgment: true
    rationale: "Same project-standing lesson as D1 — the plan requires a real-phone sign-off request for the visual result, not just automated confirmation."
  - id: D3
    description: "No desktop/tablet regression — the .data-cards toggle hides at >=960px, both migrated tables render unchanged, and w4t's scroll-edge shadow / no existing CSS selector list was disturbed"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py (130/130, full run)"
        status: pass
      - kind: automated_ui
        ref: "raw-CDP measurement — AFTER@1440 both .data-cards compute display:none, both tables display:block, stats table's 3 column widths byte-identical to BEFORE@1440's own measured widths"
        status: pass
      - kind: e2e
        ref: "scripts/run-all-tests.sh — all 16 harnesses green, coverage 92% (fail_under=83)"
        status: pass
    human_judgment: false

duration: 41min
completed: 2026-09-03
status: complete
---

# Phase quick-260903-ghy: Health mobile table fixes (UIR-10, UIR-11) Summary

**A shared `.data-cards` mobile mechanism (History's sibling-combinator toggle idiom) closes both UIR-10 (stats prose squeezed to 129px) and UIR-11 (registry table clipped mid-cell) with two per-table content shapes, four new harness checks, and a real-browser 375px/1440px before/after measurement against seeded production-shaped state.**

## Performance

- **Duration:** 41 min
- **Started:** 2026-09-03T10:03:03Z (plan commit)
- **Completed:** 2026-09-03T10:44:00Z
- **Tasks:** 3 (2 code tasks + 1 verification-only task)
- **Files modified:** 3 (`companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`)

## Accomplishments

- Added the shared `.data-cards`/`.data-card` mobile mechanism to `companion/static/style.css` — new selectors only, toggled against `.data-table-wrap` at the existing 960px breakpoint via the same sibling-combinator idiom History's `.history-cards` already establishes. Zero existing selector list or declaration edited; w4t's scroll-edge shadow, the max-content floor, and the three literal selectors the harness itself indexes by (`.data-table {`, `.data-table--prose {`, `.data-table td.desc {`) are all untouched.
- Resolution-statistics (UIR-10): `_stats_cards_html()` renders one full-width card per source — label + count on the primary line, the FULL untruncated description sentence beneath — before the unchanged `data-table--prose` desktop table. `_STATS_HEADERS` promoted to a shared module constant.
- Unresolved prefixes (UIR-11): `_registry_cards_html()` renders one card per prefix — Prefix + Count on the primary line, Last seen at rest on the secondary line, First seen + Example callsign behind a `<details>` disclosure — exactly paired with its `<tr>` by a new shared `_registry_filter_text()` helper and the identical loop index, so the two representations can never diverge on filter text or group. `_REGISTRY_HEADERS` promoted to a shared module constant.
- Four new harness checks added (`EXPECTED_CHECK_COUNT` 126 -> 128 -> 130, re-derived by running the harness, not by arithmetic); one pre-existing check (`_anomaly_detail_list_markup_is_gone`) retargeted from a page-wide `<ul>`/`<li>` ban onto the anomaly banner's own element slice, per the plan's explicit instruction.
- Real-browser (raw-CDP, cached Playwright Chromium, legacy `--headless`) before/after measurement at 375px and 1440px against a seeded copy of production-shaped state (`/tmp/skypane-prod-state`), including a live `<details>`-open and filter-input interaction. Screenshots captured. See "Real-Browser Verification" below for the full measurement table.

## Task Commits

1. **Task 1: Shared `.data-cards` mechanism + Resolution-statistics mobile shape (UIR-10)** - `2b4c47e` (feat)
2. **Task 2: Unresolved-prefixes mobile shape with exact filter pairing (UIR-11)** - `4079e37` (feat)
3. **Task 3: Real-browser 375px before/after verification and full-suite green** - no code commit (verification-only; `scripts/run-all-tests.sh` run and `EXPECTED_CHECK_COUNT` reconciliation happened as part of Task 2's commit, confirmed green again here)

**Plan metadata:** not committed by this agent — the orchestrator handles the final docs commit (SUMMARY.md/STATE.md), per this dispatch's explicit constraints.

## Files Created/Modified

- `companion/pages/health_page.py` - `_STATS_HEADERS`/`_REGISTRY_HEADERS` promoted to module constants; `_stats_cards_html()` and `_registry_cards_html()` added; `_registry_filter_text()` shared helper extracted; `_registry_section()` wired to emit cards before the table; `_registry_row_html()`'s now-false "no mobile-card pairing" comment corrected in place.
- `companion/static/style.css` - New `.data-cards`/`.data-card*` rule block (list reset, row-hairline card, primary/secondary/label/desc/details parts) placed after `.history-card__details`; base hide rule (`.data-cards ~ .data-table-wrap { display: none }`) plus the inverse pair inside the existing `@media (min-width: 960px)` block.
- `companion/test_status_pages.py` - Four new checks (stats-cards completeness/order, toggle-contract/untouched-rules, registry-cards filter pairing, no-chrome/no-cross-page-leak); one existing check's allowlist extended in place (`_nested_card_heading_rhythm_end_to_end`); one existing check retargeted in place (`_anomaly_detail_list_markup_is_gone`); `history_page` added to the module's imports (for the no-cross-page-leak check); `EXPECTED_CHECK_COUNT` 126 -> 130.

## Decisions Made

- **Per-table content shape, not a shared generic builder.** `layout.data_table()` was NOT extended with a card mode — the two Health tables have genuinely different column shapes (prose vs. five short comparison values), so two 20-line page-local builders read more clearly than one generic builder needing a per-table shaping callback.
- **`.data-card__desc` repeats, rather than joins, `.data-table td.desc`'s selector list** — the harness pins that rule by an exact literal string (`.index('.data-table td.desc {')`), so appending a second selector would have broken a passing check into a `ValueError`. Repetition of the file's single 70%-muted-text literal is already this file's established practice (four other rules already do the same).
- **`.data-card__label` mirrors `.data-table th`'s label tier by VALUE, not by selector** — copied literals (11px / semibold / 0.06em / uppercase / 70% muted), pinned equal by Check B, so a future edit to one that forgets the other fails loudly instead of silently drifting.
- **Auth for the real-browser check via CDP cookie injection, not a UI-driven login form.** Documented above under `key-decisions` — a genuine property of `companion/auth.py`'s stateless HMAC session token discovered while building the verification harness, not a shortcut around the login flow's own correctness (which is untouched by this task and outside its scope).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extended a pre-existing harness check's allowlist for the new `<ul class="data-cards">` element**
- **Found during:** Task 1, first harness run after wiring `_stats_cards_html()` into `_stats_table_html()`
- **Issue:** `_nested_card_heading_rhythm_end_to_end` (quick task 260902-bl2's own check) asserts the element immediately after every nested card's `</h2>` is either `p.text-body` or a member of a small no-top-margin allowlist. The new `.data-cards` list (which already declares its own `margin: 0` list-reset) is not a member of that allowlist, so the Resolution-statistics section's seeded-state branch failed once cards existed.
- **Fix:** Added `'<ul class="data-cards">'` to the check's `allowed` tuple, with a comment explaining why (the rule's own `margin: 0` already satisfies the no-top-margin contract the allowlist exists to verify).
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** Full harness green (128/128) immediately after; re-confirmed green at 130/130 after Task 2.
- **Committed in:** `2b4c47e` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking, test-collateral only — no production code path affected)
**Impact on plan:** Zero scope creep; the fix is a one-line allowlist addition to a check the plan's own must_haves explicitly distinguish from the three checks that must NOT be touched.

## Issues Encountered

- **Real-browser login flakiness, root-caused and worked around.** While building Task 3's raw-CDP verification driver, a UI-driven login form submission against the SECOND of the two servers (before-tree and after-tree, same password, same host, different ports) became non-deterministic: `companion/auth.py`'s session token is `HMAC(password, expiry)` with no port or host component, and cookies are domain-scoped (not port-scoped) per RFC 6265 — so a cookie set while visiting either port in the same browser profile is a byte-identical, validly-signed token for the OTHER port too if minted within the same expiry second, and gets sent on requests to it. This made "is the login FORM itself still on screen" an unreliable precondition once one server had already been visited. Root-caused via CDP `Network.requestWillBeSentExtraInfo`'s `associatedCookies` field (the plain `requestWillBeSent` event does not expose the `Cookie` header at all). Worked around by establishing each server's session via a real `POST /login` (fetch, not a UI form) and handing the resulting server-issued, validly-signed cookie to the browser via CDP `Network.setCookie` — the auth token itself is completely real; only the mechanism used to place it in the browser changed. This is orthogonal to this plan's own scope (no `auth.py` file is in `files_modified`) and is recorded here as a real property of the existing auth scheme, not a defect this task fixes.
- **Automated `cloudflared tunnel` launch was blocked by this environment's own permission classifier** (a network-exposing action). See "Pending: Real-Phone Sign-Off" below for the exact command a developer can run themselves.

## Real-Browser Verification

**Method:** the established fallback (quick tasks 260903-c4o/260903-etm) — the repo's cached Playwright Chromium (`~/Library/Caches/ms-playwright/chromium-1228`), launched with legacy `--headless` (not `--headless=new`, a reproduced hang in this environment) and a fixed `--remote-debugging-port`, driven over raw CDP using Node 22's built-in `WebSocket`/`fetch` globals. No MCP Playwright tool was reachable in this environment.

**Fixture:** `/tmp/skypane-prod-state` (`history.db` + `illustration_overrides`, confirmed present, no `poll_state.json`) copied TWICE via `cp -R` into session scratch — never served from the original. `history.db`'s `runway_events` table was confirmed empty (0 rows), so both copies were seeded identically with 100 synthetic `runway_events` (40 fresh_hit / 25 cache_hit / 15 airline_only / 20 miss, over the last 100 hours — well inside `RESOLUTION_WINDOW_DAYS=30`) to make the Resolution-statistics table non-empty, plus 6 unresolved prefixes (`AFR`, `EZY`, `TVF`, `VLG`, `WZZ`, `DAH`; counts 7-63; `first_seen`/`last_seen` 3-20 days apart) via `poll_loop.save_poll_state()`, matching production-shaped data.

**Trees:** BEFORE = `git archive 791caaa70cfea889e5988d4857ee0ef5296c491c` (this plan's own recorded `BASE_SHA`, Task 1's first action) extracted into scratch, served on port 8791 against the first seeded copy. AFTER = the current branch's working tree, served on port 8792 against the second seeded copy.

### Before/After Measurement Table (375px)

| Metric | BEFORE | AFTER |
|---|---|---|
| Stats Description column width (audit cited ~129px) | **115.7px** (audit's own figure does not exactly reproduce here — reported honestly, not corrected to match) | n/a — column no longer exists on mobile; see card measurements |
| First stats row height (audit cited ~171px) | **171px** (matches audit exactly) | n/a — replaced by cards |
| `.data-cards` (stats) exists / visible | false / — | **true / visible, `display: block`** |
| Stats desktop table `display` | `block` (only representation) | **`none`** (hidden by the toggle) |
| Every stats description paragraph `scrollWidth <= clientWidth` | n/a | **true, all 4** (293<=293 each — zero clipping) |
| Every stats description `textContent` == full `_SOURCE_ROWS` gloss | n/a | **true, all 4** (untruncated) |
| Tallest stats card item height | 171px (table row) | **141px** (card) |
| Registry wrap `scrollWidth` vs `clientWidth` | **737px vs 293px** (444px of clipped content — reproduces UIR-11) | n/a — registry table hidden behind the toggle on mobile |
| `.data-cards` (registry) exists / visible | false / — | **true / visible, `display: block`, 6 cards** |
| Registry desktop table `display` | `block` (only representation) | **`none`** (hidden by the toggle) |
| Page `scrollHeight` (375px) | 3452px | 3153px (shorter, more compact) |

### Desktop No-Regression Gate (1440px, AFTER tree)

| Check | Result |
|---|---|
| Both `.data-cards` lists compute `display: none` | **pass** (2/2) |
| Both `.data-table-wrap` tables compute `display: block` | **pass** (2/2) |
| Stats table's 3 column widths, AFTER vs BEFORE | **byte-identical**: `[125.4375, 789.484375, 76.078125]` both trees |

### Live Interaction Exercise (AFTER tree, 375px)

- Clicked the first registry card's `<details>` summary ("More details") — `details.open` became `true`; the `<dl>` text read `"First seen10:16 UTC (20d ago)Example callsignTVF902"` (non-empty, real values).
- Typed the seeded prefix `tvf` into the filter input and dispatched a real `input` event — visible card count became `1`, and `[data-filter-count]` read **`"1 of 6 shown"`** (N, the true seeded prefix count — NOT 2N=12, confirming the group-pairing gate holds in a live browser, not just in the harness).

**Screenshots** (session scratch, not committed — outside the repository):
- `before-375.png` — reproduces both defects: the Description column squeezed to one-word-per-line rows, and the registry table clipped mid-cell with Last seen/Example callsign fully off-screen.
- `after-375.png` — both card lists rendering cleanly, full sentences, no clipping.
- `after-1440.png` — desktop layout unchanged, both card lists hidden, both tables visible.

## Pending: Real-Phone Sign-Off

Per this project's own standing lesson (`feedback_real_device_ui_verification`: computed-style checks alone once missed a real mobile nav bug), the visual outcome above is NOT presented as settled — it is flagged for a developer's own real-phone confirmation, matching quick task 260903-etm's closing precedent.

Automating a `cloudflared` quick tunnel was attempted but **blocked by this environment's own permission classifier** (a network-exposing action). The developer can run this themselves against the seeded AFTER copy to get an HTTPS URL reachable from a real phone (`Secure` session cookies require HTTPS off-localhost):

```
cloudflared tunnel --url http://127.0.0.1:8792
```

...with the AFTER server still running against the seeded copy (`companion/app.py --port 8792 --state-dir <after-copy>`, `SKYPANE_COMPANION_PASSWORD` set). Both the AFTER server and the tunnel were stopped at the end of this task's own verification run; a developer re-running the above would need to first restart the server against a freshly-seeded copy (the exact seeding recipe is recorded under "Fixture" above).

**What to check on a real phone:** both Health tables at native device width — full description sentences on Resolution statistics with no clipping, and every unresolved prefix's Last seen visible at rest with First seen/Example callsign one tap away behind "More details".

## Test Harness Results

Full suite via `scripts/run-all-tests.sh` (all 16 canonical harnesses):

| Harness | Result |
|---|---|
| config-history | 30/30 |
| dither | 6/6 |
| enrich | 52/52 |
| illustrations | 58/58 |
| panel-preview | 11/11 |
| pipeline-e2e | 6/6 |
| plane-detection | 47/47 |
| poll-loop | 44/44 |
| render | 119/119 |
| runway-config | 14/14 |
| poll-cycle | 23/23 |
| companion-app | 125/125 |
| config-page | 64/64 |
| contrast-check | 36/36 |
| **status-pages** | **130/130** (126 -> 130, four new checks, `EXPECTED_CHECK_COUNT` re-derived from a real run each time) |
| view-pages | 52/52 |

Coverage: **92%** (threshold `fail_under = 83` in `pyproject.toml`). `server/.venv/bin/ruff check .` clean.

**Out-of-scope diff confirmation:** `git diff --stat -- companion/pages/history_page.py companion/pages/airlines_page.py companion/layout.py companion/app.py companion/static/list-filter.js server/` is empty after both code tasks — zero cross-page leak, matching the plan's own hard constraint.

**Three protected checks confirmed unmodified and green:** `_prose_table_opts_out_alone`, `_desc_column_muted_end_to_end`, and the mono-span-count floor at (now-shifted) line ~1117 (`_device_and_pipeline_rows_use_concise_timestamp_format`) — none needed an edit, none were touched.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UIR-10 and UIR-11 are both closed in code and automated-test terms; the real-phone sign-off request above is the one remaining open item, matching this project's standing verification practice for mobile UI changes.
- `06.6.4.1-UI-REVIEW.md`'s remaining open items (per STATE.md as of this task's start): the Settings theme picker (UIR-01/02) and the UIR-20..26 typography/spacing direction items — unaffected by this task, still open.
- This task stayed entirely within `companion/pages/health_page.py`, `companion/static/style.css`, and `companion/test_status_pages.py`, on the current branch `claude/health-mobile-tables-uir-10-11` — no new branch, no re-fork.

---
*Phase: quick-260903-ghy*
*Completed: 2026-09-03*

## Self-Check: PASSED

- FOUND: `companion/pages/health_page.py`
- FOUND: `companion/static/style.css`
- FOUND: `companion/test_status_pages.py`
- FOUND: `.planning/quick/260903-ghy-health-mobile-tables-from-06-6-4-1-ui-re/260903-ghy-SUMMARY.md`
- FOUND commit: `2b4c47e` (Task 1)
- FOUND commit: `4079e37` (Task 2)
