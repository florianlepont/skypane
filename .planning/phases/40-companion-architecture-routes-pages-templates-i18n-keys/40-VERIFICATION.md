---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
verified: 2026-09-27T23:03:13Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 40: Companion architecture — routes, pages, templates, i18n keys Verification Report

**Phase Goal:** A route cannot be exposed by forgetting a line; pages are split by responsibility with typed context; templates use names not positions; CSS de-duplicated and tokenised; translations keyed by stable IDs.
**Verified:** 2026-09-27T23:03:13Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria + requirement rows)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every route declared once in a table; a test proves every non-public route requires a session | VERIFIED | `companion/routes.py` — one `ROUTES` tuple of `Route(method, matcher, handler, auth_required)`; `auth_required=False` only for `/login` (GET/POST) and the 18 `static_files.STATIC_ROUTES` entries. `companion/test_route_table.py` builds a real sample path per matcher and hits a real running server with no session cookie, asserting the response equals a committed pre-refactor baseline (303→`/login`). Ran directly: 30/30 tests pass, including `test_public_routes_are_exactly_login_and_static_assets`, `test_every_baseline_route_is_in_the_table`, `test_every_handler_resolves`. |
| 2 | No companion file over ~1500 lines; no function over 80 code lines | VERIFIED | `companion/test_structure_guards.py` measures via `test-support/companion_structure.py` (ast-based, outside the G2-scanned test files). `PENDING_OVERSIZED_FILES`/`PENDING_LONG_FUNCTIONS` allowlists do not exist anywhere in the tree (grep confirmed) — only `TRACKED_FILE_EXCEPTIONS = {"companion/static/style.css": <reason>}` remains, with a non-empty-reason test. `wc -l` over every `companion/**/*.py` file confirms the largest production file (`companion/pages/airlines_page.py`) is 1384 lines, well under 1500; `style.css` is the one named exception. Guard tests ran and passed. |
| 3 | No duplicated CSS selector; no hard-coded colour outside tokens | VERIFIED | `companion/test_stylesheet_structure.py` parses the served stylesheet with `companion_markup.css_rules()` (never regex/substring per G11) and asserts no selector repeats within an at-rule context and no colour literal appears outside a custom-property definition. Ran directly: 2/2 pass. Nine new tokens and 19 merged selectors documented in `sketch-findings-skypane/references/accessibility-contrast.md`, matching `git log` evidence (`27b7484 feat(40-02): dedupe every selector and tokenise every colour literal`). |
| 4 | Rewording an English string cannot drop its French translation | VERIFIED | `companion/i18n.py`'s `Message`/`msg()`/`REGISTRY` mechanism: French is looked up by `msg_id` in `companion.i18n_fr.BY_ID`, never by English text. `companion/test_i18n.py::test_rewording_the_english_keeps_the_french` and `test_t_lang_reworded_english_keeps_its_french_translation` both pass. `i18n.t()`/`t_lang()` call `_require_message()` and raise `TypeError` on a plain `str` — confirmed by reading `companion/i18n.py:83-100` and running `test_plain_strings_are_refused` (passes). Legacy English-keyed `CATALOG` fallback fully removed (40-15). |
| 5 | CMP-04: typed per-page context replaces the `page_context()` god dict | VERIFIED | `companion/page_context.py`'s `PageContext` preserves `_LazyContext`'s laziness invariants (one `health_signals()` read per tab, shared `_calendar_registry`, at-most-once lazy resolution). `companion/test_page_context.py` (32 tests, run directly) passes in full. |
| 6 | CMP-05: named templates, byte-identical output | VERIFIED | `companion/ui_shell.py`'s `page_shell()`/`login_shell()` use `str.format_map()` over a named dict; `layout.py` is a re-export facade. `companion/test_render_baseline.py` (byte-equality against a committed pre-refactor baseline) passes. |
| 7 | CFG-34: three live relative-age sites converted, fourth enumerated as exception | VERIFIED | `history_page.py`, `settings/calendar.py`, `health_page.py` all call `layout.relative_time_html()` inline (bypassing `_merged_cell()`/`status_row()`'s unconditional escaping to avoid double-escaping). `test_cfg34_live_age_ticks_at_each_converted_site` (3 parametrized cases, real Chromium + virtual clock) passes; this test was previously blocked by a pre-existing cross-phase bug (`server.poll_loop.save_poll_state` missing), logged in `deferred-items.md` and independently fixed in commit `6264c71` — now green. |
| 8 | CFG-39: battery chart migrated onto `draw.py`'s shared primitives | VERIFIED | `companion/battery_chart.py`'s `sparkline_point_y` is `functools.partial(draw.percent_y, ...)` (identical function object); every shape emitted via `draw.rect`/`draw.line`/`draw.circle`/`draw.polygon`/`draw.area_canvas`/`draw.label_span`. `test_battery_chart_markup_is_unchanged` and the drawing-contract tests in `test_companion_app_02.py` pass. |
| 9 | CFG-52: artwork drop zone keyboard-only operability measured, fixed if failing | VERIFIED | `companion/test_browser_ux_04.py::test_the_artwork_drop_zone_is_operable_from_the_keyboard_alone[light|dark]` drives Tab→Space→file-chooser→Tab→Enter with a pointer-event recorder armed throughout, asserting zero pointer events and a file readable back from disk. Real browser test, not a source-text check. |
| 10 | WR-01 code-review fix landed (i18n bypass in `data_table()`'s empty-rows fallback) | VERIFIED | Commit `2f81629` replaced the two bare English literals with `i18n.msg()` Messages (`common.no_data_yet`, `common.nothing_to_show_here_yet`); French entries present in `companion/i18n_fr/common.py`; call site now uses `i18n.t(...)`. |
| 11 | Requirement IDs CMP-01..09, CFG-34, CFG-39, CFG-52 all traced and ticked | VERIFIED | `.planning/REQUIREMENTS.md` ticks all 12 with per-clause evidence and named tests; cross-checked against actual test files and code — all named tests exist and pass. No orphaned requirement rows found for Phase 40. |
| 12 | Full test suite green, coverage at/above the 93% floor | VERIFIED | Independently re-ran (not trusting SUMMARY.md): `pytest companion/ test-support/ -n auto` → **2056 passed, 3 skipped, 0 failed** (matches SUMMARY's claimed number exactly). `./scripts/run-all-tests.sh` (full repo, with coverage) → **3211 passed, 7 skipped, 0 failed**, coverage **94.86%** (floor 93%) — matches the claimed 3211 exactly. |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `companion/routes.py` | Route/Exact/PrefixSuffix/ROUTES/match() | VERIFIED | Read in full; single table, both GET/POST, correct auth_required scoping |
| `companion/static_files.py` | STATIC_ROUTES allowlist + cache | VERIFIED | Referenced correctly by routes.py and test_route_table.py |
| `companion/page_context.py` | PageContext, build_page_context, coerce | VERIFIED | Read; laziness/sharing invariants documented and tested |
| `companion/ui_shell.py`, `ui_time.py`, `ui_nav.py`, `ui_components.py` | layout.py split by responsibility | VERIFIED | layout.py is now a re-export facade; all ui_*.py modules exist |
| `companion/settings/*.py` | per-settings-group modules | VERIFIED | theme.py, quiet_hours.py, wake_interval.py, calendar.py, rules.py, runway_led.py, notifications.py, form.py, form_post.py all present |
| `companion/battery_chart.py`, `health_signals.py` | chart + signal extraction | VERIFIED | Both exist, both import draw.py primitives, both covered by tests |
| `companion/i18n.py` (Message/msg/REGISTRY) | stable-ID mechanism | VERIFIED | Read in full; `_require_message` rejects plain str |
| `companion/test_route_table.py`, `test_structure_guards.py`, `test_stylesheet_structure.py`, `test_i18n.py`, `test_page_context.py` | guard/coverage tests | VERIFIED | All read and executed directly; all pass |
| `companion/testdata/render_baseline.json`, `battery_chart_baseline.json` | committed baselines | VERIFIED | Present; render-baseline equality tests pass |
| `.planning/REQUIREMENTS.md` | updated traceability | VERIFIED | All 12 requirement IDs ticked with test-name evidence, cross-checked against real files |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `companion/app.py Handler._dispatch` | `companion/routes.py match()` | single dispatch helper | WIRED | Confirmed by reading routes.py's Route tuples and app.py wiring pattern |
| `companion/routes.py` | `companion/static_files.py STATIC_ROUTES` | one public Route per allowlist entry | WIRED | `_static_get_routes()` iterates `static_files.STATIC_ROUTES` directly |
| `companion/layout.py` | `companion/ui_*.py` | re-export imports | WIRED | layout.py is confirmed a facade; all call sites still resolve (render-baseline equality proves this) |
| `companion/battery_chart.py` | `companion/draw.py` | `draw.percent_y`/`rect`/`line`/`circle`/`polygon`/`label_span` | WIRED | Grepped and confirmed; `sparkline_point_y` is a `functools.partial` of the real function |
| `companion/i18n.py t()/t_lang()` | `companion.i18n_fr.BY_ID` | ID-keyed lookup | WIRED | `_translate_fr` looks up by `msg_id`; plain str raises TypeError |
| `companion/test_route_table.py` | real running server | HTTP requests, no cookie | WIRED | Test uses `companion_app_server.http_request()` against a live `module_app_server_factory()` instance — genuine integration test, not source introspection |

### Behavioral Spot-Checks / Direct Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Structure guards (file/function ceilings) | `pytest companion/test_structure_guards.py` | 3 passed | PASS |
| Route table auth coverage | `pytest companion/test_route_table.py` | 30 passed | PASS |
| i18n stable-ID contract (incl. plain-str rejection) | `pytest companion/test_i18n.py` | 34 passed | PASS |
| Typed PageContext laziness invariants | `pytest companion/test_page_context.py` | 32 passed | PASS |
| Render baseline byte-equality | `pytest companion/test_render_baseline.py` | included in 32-test run above | PASS |
| Static cache (ETag/304/Cache-Control) regression | `pytest companion/test_static_cache.py` | included above | PASS |
| Stylesheet structure (dedup + colour-token) guard | `pytest companion/test_stylesheet_structure.py` | 2 passed | PASS |
| Phase-38 regression suites (page_scripts, freshness_token, request_connections) | `pytest companion/test_page_scripts.py test_freshness_token.py test_request_connections.py` | 70 passed, 1 skipped (root-only) | PASS |
| CFG-34 live-age ticking (real browser, virtual clock) | `pytest companion/test_browser_ux_03.py::test_cfg34_live_age_ticks_at_each_converted_site` | 3 passed | PASS |
| CFG-39 battery chart contract | `pytest companion/test_companion_app_02.py -k "drawing or battery"` | 5 passed | PASS |
| CFG-52 keyboard-only drop zone | present in `companion/test_browser_ux_04.py`, read and confirmed genuine (real Playwright `expect_file_chooser`, pointer recorder) | not re-run individually but covered by full-suite pass | PASS |
| Full companion + test-support suite | `pytest companion/ test-support/ -n auto` | **2056 passed, 3 skipped, 0 failed** | PASS |
| Full repository suite with coverage gate | `./scripts/run-all-tests.sh` | **3211 passed, 7 skipped, 0 failed, coverage 94.86% (floor 93%)** | PASS |

### Debt-Marker / Anti-Pattern Scan

Scanned every file touched by Phase 40 commits (96 files, diffed against the pre-phase base commit) for `TBD`/`FIXME`/`XXX` (blocker-gate markers) and `TODO`/`HACK`/`PLACEHOLDER`/"coming soon"/"not yet implemented"/"not available": **zero matches**. The only "hack" hit was a benign CSS comment about selector specificity ("not a specificity hack"), and every "placeholder" hit was a legitimate HTML `placeholder` attribute, string-substitution placeholder, or documented UI element — none is a stub or debt marker.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| CMP-01 | 40-01, 40-03 | Route table `(method, matcher, handler, auth_required)` | SATISFIED | `companion/routes.py`, `test_route_table.py` (30 tests, all pass) |
| CMP-02 | 40-03 | One `{route: path}` static allowlist | SATISFIED | `companion/static_files.py`, wired into routes.py |
| CMP-03 | 40-01, 40-04, 40-05, 40-06, 40-08, 40-09, 40-11 | Split by settings group/responsibility, no file over ~1500 lines | SATISFIED | `test_structure_guards.py`; largest production `.py` file measured at 1384 lines |
| CMP-04 | 40-11 | Typed per-page context | SATISFIED | `companion/page_context.py`, `test_page_context.py` (32 tests) |
| CMP-05 | 40-04 | Named templates, byte-identical output | SATISFIED | `companion/ui_shell.py` (`str.format_map`), `test_render_baseline.py` |
| CMP-06 | 40-01, 40-03..40-08, 40-16 | No function over 80 code lines | SATISFIED | `test_structure_guards.py::test_no_production_function_exceeds_the_code_line_ceiling` |
| CMP-07 | 40-09 | Shared body-drain / cookie helpers | SATISFIED | `companion/request_body.py` (`drain_capped_body`), shared cookie builder confirmed in app.py |
| CMP-08 | 40-02 | No duplicated CSS selector, no hard-coded colour outside tokens | SATISFIED | `test_stylesheet_structure.py` (parser-based, 2 tests pass); skill doc updated |
| CMP-09 | 40-12..40-15 | Stable message IDs | SATISFIED | `companion/i18n.py`, `test_i18n.py` (34 tests incl. completeness/orphan/rewording/plain-str-refused) |
| CFG-34 | 40-10 | Three live relative-age sites converted | SATISFIED | Real-browser virtual-clock test passes; 4th (battery tooltip) correctly enumerated as structural exception |
| CFG-39 | 40-06 | Battery chart on `draw.py`'s shared drawing contract | SATISFIED | `battery_chart.py` built entirely on `draw.py` primitives, byte-identical baseline test passes |
| CFG-52 | 40-07 | Artwork drop zone keyboard-only measurement | SATISFIED | Real Playwright keyboard-only test with pointer-event recorder |

No orphaned requirements found: `.planning/REQUIREMENTS.md`'s Phase-40 traceability rows (lines 438-446) list exactly these 12 IDs, matching the phase's declared requirement set and every plan's own `requirements:` frontmatter field.

### Human Verification Required

None. Every must-have here is machine-verifiable (structural guards, route-table coverage against a real server, parser-based CSS checks, runtime i18n registry checks, and real-browser Playwright tests for the two UX-shaped items, CFG-34 and CFG-52) and all were independently re-executed in this verification session rather than trusted from SUMMARY.md.

### Gaps Summary

None. All 12 must-haves (4 ROADMAP success criteria plus the 12 requirement IDs, which overlap and reinforce each other) are independently verified against the live codebase: read the actual implementation files, confirmed the code review's one warning (WR-01) was fixed and correctly wired, and re-ran the full test suite twice (companion-scoped: 2056 passed; whole-repo with coverage gate: 3211 passed, 94.86% coverage) rather than trusting the SUMMARY.md's reported numbers — both runs matched the claimed figures exactly.

---

_Verified: 2026-09-27T23:03:13Z_
_Verifier: Claude (gsd-verifier)_
