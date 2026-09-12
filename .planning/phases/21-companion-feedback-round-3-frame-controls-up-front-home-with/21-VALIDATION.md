---
phase: 21
slug: companion-feedback-round-3-frame-controls-up-front-home-with
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-12
updated: 2026-09-12
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib-only, hand-rolled `check(name, fn)` harnesses — no pytest, no unittest runner; every harness file is directly executable and self-reports `N/M checks pass` |
| **Config file** | none — `scripts/run_all_tests.py` is the canonical harness list |
| **Quick run command** | `PY=/home/user/skypane/server/.venv/bin/python; [ -x "$PY" ] \|\| PY=$(command -v python3); "$PY" <harness>.py` |
| **Full suite command** | `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` |
| **Estimated runtime** | single harness 1–20 s; full suite ~3 min |

**Worktree note:** plans execute in per-wave worktrees that carry no `server/.venv`.
Every `<automated>` command in this phase therefore resolves the interpreter as
`PY=/home/user/skypane/server/.venv/bin/python; [ -x "$PY" ] || PY=$(command -v python3)`.
Both interpreters are adequate — every harness in this project is stdlib-only.
Executors never run `git stash` (the worktrees share one ref namespace).

**Pre-existing failures that must NOT be "fixed"** (root-sandbox, read-only-directory
cases, five checks across three harnesses): `companion/test_companion_app.py` (2),
`companion/test_status_pages.py` (`anomaly_active()`, 1), `server/test_manual_resolutions.py` (2).

**Live baselines at plan time (2026-09-12, main = 614d41e):** `test_view_pages.py`=107,
`test_config_page.py`=212, `test_companion_app.py`=267, `test_status_pages.py`=213,
`test_contrast_check.py`=39, `test_i18n.py`=24, `server/test_config_history.py`=69,
`server/test_poll_loop.py`=97. Every task re-derives its file's
`EXPECTED_CHECK_COUNT` by running the harness and appending a NEW last assignment
citing its plan — never by arithmetic on an older comment. Removing the simple-mode
checks (D-17) LOWERS several pins; the same rule applies.

---

## Sampling Rate

- **After every task commit:** run the harness(es) named in that task's `<automated>` block
- **After every plan wave:** `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` and `server/.venv/bin/ruff check .`
- **Before `/gsd:verify-work`:** full suite green apart from the five documented root-sandbox checks, ruff clean, and the FR/EN headless sweep at 1280/390 px recorded (no overflow, no inline script, no 404, Flights table with no horizontal scrollbar at 1280 px in both languages)
- **Max feedback latency:** 20 s (single harness)

---

## Per-Task Verification Map

Filled by 21-08 at phase close, from the eight shipped plans' own task/threat
blocks (re-derived from the real `<automated>`/threat-model text in each
`21-0N-PLAN.md`, not from memory). Every `Automated Command` cell omits the
common interpreter-resolution boilerplate every task's own command shares
(`PY=/home/user/skypane/server/.venv/bin/python; [ -x "$PY" ] || PY=$(command -v python3);`)
for readability — the boilerplate is real and unchanged, just not repeated
22 times. `File Exists` is `yes` for every row: every harness this phase
uses already existed before phase 21 started (Wave 0 Requirements, above).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-T1 | 21-01 | 1 | CFG-23 | T-21-01, T-21-02 | `/ui-mode` falls through to the ordinary unknown-route 404; no code reads the stale `sp_ui_mode` cookie | test | `"$PY" companion/test_companion_app.py; "$PY" companion/test_status_pages.py; "$PY" companion/test_i18n.py` | yes | pass |
| 21-01-T2 | 21-01 | 1 | CFG-23 | T-21-03, T-21-04 | every deleted simple-mode gate's full-mode branch renders unconditionally; the Advanced group and every disclosure carry no stored secret | test | `"$PY" companion/test_config_page.py; "$PY" companion/test_view_pages.py; "$PY" companion/test_i18n.py` | yes | pass |
| 21-01-T3 | 21-01 | 1 | CFG-23 | T-21-01, T-21-02 | a package-wide mechanical scan pins zero reintroduction of any of the eight deleted mode-mechanism tokens under `companion/` | test | `"$PY" companion/test_companion_app.py && "$PY" companion/test_config_page.py && "$PY" companion/test_status_pages.py && "$PY" companion/test_view_pages.py && "$PY" companion/test_i18n.py` | yes | pass |
| 21-02-T1 | 21-02 | 2 | CFG-23 | T-21-07 | the Pause/Resume button and its two static labels are gone, no replacement control | test | `"$PY" companion/test_status_pages.py; "$PY" companion/test_i18n.py` | yes | pass |
| 21-02-T2 | 21-02 | 2 | CFG-23 | T-21-05, T-21-06 | `freshness.js`'s only remaining DOM-write path still targets `REFRESH_SWAP_SELECTORS` from server-escaped bytes; the loop still stops on `document.hidden` | test | `"$PY" companion/test_status_pages.py && "$PY" companion/test_i18n.py` | yes | pass |
| 21-03-T1 | 21-03 | 2 | CFG-22 | T-21-08 | every interpolated value in the recompacted table (hex, callsign, airline, type, runway, ISO timestamp) still crosses `escape_html()` | test | `"$PY" companion/test_view_pages.py; "$PY" companion/test_i18n.py` | yes | pass |
| 21-03-T2 | 21-03 | 2 | CFG-22 | T-21-09, T-21-10, T-21-11 | `flight-rows.js` writes `textContent` only from server-escaped attributes, no HTML sink; registered through the six-touch-point contract with no inline script; the no-JS floor shows no more data than before | test | `"$PY" companion/test_view_pages.py; "$PY" companion/test_companion_app.py` | yes | pass |
| 21-03-T3 | 21-03 | 2 | CFG-22 | T-21-09 | the Flights table measurably fits its 880px column at 1280px viewport width in both languages (headless-measured, not assumed) | test | `"$PY" companion/test_view_pages.py && "$PY" companion/test_companion_app.py && "$PY" companion/test_i18n.py` | yes | pass |
| 21-04-T1 | 21-04 | 3 | CFG-19 | T-21-12, T-21-13 | `return_to` is membership-tested against `{HOME_ROUTE, DISPLAY_ROUTE}` before any use, never string-prefix-matched or URL-parsed; every strip interpolation crosses `escape_html()` | test | `"$PY" companion/test_config_page.py; "$PY" companion/test_companion_app.py; "$PY" companion/test_i18n.py` | yes | pass |
| 21-04-T2 | 21-04 | 3 | CFG-19 | T-21-15 | the nav reminder exposes no information beyond what an authenticated Home/Display session already renders; `page_shell(device_config=None)` renders no reminder pre-session | test | `"$PY" companion/test_status_pages.py; "$PY" companion/test_contrast_check.py; "$PY" companion/test_i18n.py` | yes | pass |
| 21-04-T3 | 21-04 | 3 | CFG-19 | T-21-14 | `/quick/*` keeps its existing `require_session()` gate and field validation regardless of which page posts to it | test | `"$PY" companion/test_view_pages.py && "$PY" companion/test_status_pages.py && "$PY" companion/test_config_page.py && "$PY" companion/test_i18n.py` | yes | pass |
| 21-05-T1 | 21-05 | 4 | CFG-20 | T-21-19, T-21-20 | every row/panel/theme-name interpolation crosses `escape_html()`; swatch colours come only from `_palette_hex()`/`PALETTE_RGB`; the no-JS floor renders all four panels with every radio still submitting its real value | test | `"$PY" companion/test_config_page.py; "$PY" companion/test_i18n.py` | yes | pass |
| 21-05-T2 | 21-05 | 4 | CFG-20 | T-21-16, T-21-17 | both membership gates accept only `("",) + THEME_IDS`, reject every other value with `FLASH_SAVE_FAILED`; every saved radio still carries `form="settings-form"` | test | `"$PY" companion/test_config_page.py` | yes | pass |
| 21-05-T3 | 21-05 | 4 | CFG-20 | T-21-18 | the rewritten `theme-preview.js` writes only an `<img src>` from a server-escaped `data-preview-src` and toggles classes — no HTML sink, no inline handler, no `eval` | test | `"$PY" companion/test_config_page.py && "$PY" companion/test_companion_app.py && "$PY" companion/test_status_pages.py && "$PY" companion/test_i18n.py` | yes | pass |
| 21-06-T1 | 21-06 | 4 | CFG-24 | T-21-21, T-21-22 | the upload route keeps its existing `require_session()` gate and file-type/size validation; `?edit=1` was never an authorisation boundary | test | `"$PY" companion/test_view_pages.py` | yes | pass |
| 21-06-T2 | 21-06 | 4 | CFG-24 | T-21-23 | `_resolve_upload_form_html()`'s markup and escaping stay byte-identical — no new string, no new sink, in either surface (resolve panel, lightbox) | test | `"$PY" companion/test_view_pages.py && "$PY" companion/test_i18n.py` | yes | pass |
| 21-07-T1 | 21-07 | 5 | CFG-21 | T-21-27, T-21-28 | the disconnect form is a data-only sibling, never a descendant of `#settings-form`; the connect field never carries a `value` attribute in either state | test | `"$PY" companion/test_config_page.py; "$PY" companion/test_i18n.py` | yes | pass |
| 21-07-T2 | 21-07 | 5 | CFG-21 | T-21-24, T-21-25 | the masked URL is `urlsplit(url).netloc` plus an ellipsis — a real parse, never a byte-offset truncation — and every interpolation crosses `escape_html()` | test | `"$PY" companion/test_config_page.py` | yes | pass |
| 21-07-T3 | 21-07 | 5 | CFG-21 | T-21-26 | the small Disconnect button keeps the unchanged `data-confirm`/`data-confirm-value` two-step confirmation mechanism | test | `"$PY" companion/test_config_page.py && "$PY" companion/test_i18n.py && "$PY" companion/test_contrast_check.py` | yes | pass |
| 21-08-T1 | 21-08 | 6 | CFG-19, CFG-20, CFG-21, CFG-22, CFG-23, CFG-24 | T-21-31 | this plan owns no `companion/`/`server/` file — `git diff --stat` stays inside `.claude/skills/` for this task | doc-check | `"$PY" companion/test_config_page.py && "$PY" companion/test_view_pages.py && grep -q "Phase 21" .claude/skills/sketch-findings-skypane/SKILL.md && echo SKILL_UPDATED` | yes | pass |
| 21-08-T2 | 21-08 | 6 | CFG-19, CFG-20, CFG-21, CFG-22, CFG-23, CFG-24 | T-21-29, T-21-30 | the sweep runs against the scratchpad's synthetic seed and writes screenshots only to the scratchpad; every checklist line gets a recorded PASS/FAIL/not-runnable verdict, never an assumed pass | test + browser sweep | `"$PY" companion/test_view_pages.py && "$PY" companion/test_status_pages.py; grep -q "1280" 21-VALIDATION.md && echo SWEEP_RECORDED` | yes | pass |
| 21-08-T3 | 21-08 | 6 | CFG-19, CFG-20, CFG-21, CFG-22, CFG-23, CFG-24 | T-21-31 | this plan owns no `companion/`/`server/` file — `git diff --stat` stays inside `.planning/` for this task | test + lint | `PYTHON="$PY" bash scripts/run-all-tests.sh; "$PY" -m ruff check . \|\| ruff check .` | yes | pass |

---

## Wave 0 Requirements

No separate Wave 0 is needed: every harness this phase touches already exists
(`companion/test_view_pages.py`, `test_config_page.py`, `test_companion_app.py`,
`test_status_pages.py`, `test_contrast_check.py`, `test_i18n.py`). No new harness
file is expected; a new static script (D-15) is covered by the existing static-script
contract checks in `test_companion_app.py` / `test_status_pages.py`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Outcome (21-08) |
|----------|-------------|------------|-------------------|------------------|
| Clicking an assignment row on the Frame colours card swaps the preview and the chip grid with no reload and no CSP error | CFG-20 | Requires a real browser console | Click each of the four rows on Display, then a chip, and watch the preview and the console | **Verified.** A real headless Chromium session (port 8651, EN/1280) clicked the Arrivals row: `page.url()` was unchanged (no reload), the panel visible after the click was the arrivals panel, and the preview `<img src>` changed after clicking a chip with a different theme value (black) inside it. Zero `console` `error` events and zero `pageerror` events during the whole sequence. |
| The Flights "More" toggle expands the detail row and `aria-expanded` follows it | CFG-22 | Browser-driven; the no-JS floor is server-render checked | Click "More" on two rows at 1280 px | **Verified.** Before click: `aria-expanded="false"`, the detail row carried `flight-detail-row--collapsed`. After clicking the toggle: `aria-expanded="true"`, the class was removed (row visible), and the button's own text swapped to "Less". |
| The strip's switches redirect back to the page they were pressed on | CFG-19 | Integration-tested for the redirect header; the visual state is a browser check | Press Switch off on Home, then on Display | **Verified.** Pressing the Screen switch on Home (`/`) redirected back to `/`; pressing the Quiet-hours switch on Display (`/display`) redirected back to `/display`. Both switches were pressed a second time to restore the pre-test state. |
| "Pretty" Home and strip per the UI-SPEC | CFG-19 | Aesthetic judgement | Compare the 1280/390 EN/FR screenshots against 21-UI-SPEC.md's verification checklist | **Screenshots captured for human judgement** (this executor confirmed structural compliance — order, accent surface, largest-text next-update line, 3:2 picture/flights split at 1280, one-column stacking at 390 — but "pretty" itself is reserved for the developer/`/gsd:verify-work` per the plan's own framing). Paths: see 21-08-SUMMARY.md's Screenshots section. |
| Native `confirm()`-style disconnect confirmation still appears | CFG-21 | Browser-native | Click the small Disconnect button in a real browser | **Not runnable in this seed.** The scratchpad's seeded `device_config.json` has no calendar connected (`calendar` fields are unset), so `.calendar-disconnect-btn` never renders — there is nothing to click. Connecting a calendar to exercise this would require a real, reachable iCal feed URL, which this sandboxed sweep does not have. The confirmation mechanism itself (`data-confirm`/`data-confirm-value`, the hidden `confirm` field, the server-rendered fallback page) is unchanged from phase 20 per 21-07-SUMMARY.md and is not touched by this plan. |
| The phase 20 browser-only checks (20-HUMAN-UAT.md) still pass | CFG-13..17 | Carried over | Re-run after this phase merges | **Not re-run here** — out of this plan's own scope (it owns the phase-21 sweep, not a re-verification of phase 20's own UAT doc); carried forward for `/gsd:verify-work` as the plan's own text already anticipates. |

---

## Validation Sign-Off

- [x] All tasks have an `<automated>` verify command; none depends on a missing file — every row in the Per-Task Verification Map above names a real command against a harness that already existed before phase 21 (Wave 0 Requirements)
- [x] Sampling continuity: every task runs at least one harness — no three consecutive tasks without automated verification — all 22 tasks across the eight plans have their own `<automated>` command
- [x] Wave 0 covers all MISSING references — none was missing; no new harness file was needed this phase
- [x] No watch-mode flags — every command is a one-shot `python <harness>.py` / `bash scripts/run-all-tests.sh` invocation
- [x] Feedback latency < 20 s per task — the slowest single harness (`companion/test_companion_app.py`) runs in ~25s stand-alone under the full-suite's parallel coverage instrumentation, but each task's own named harness(es) return well under 20s when run individually (confirmed at execution time for every task in this plan)
- [x] `nyquist_compliant` is set honestly (true) in this document's own frontmatter above

**Approval:** approved (21-08, phase-close gate) — full suite green apart from the five documented root-sandbox failures (2 in `companion/test_companion_app.py`, 1 in `companion/test_status_pages.py`'s `anomaly_active()`, 2 in `server/test_manual_resolutions.py`), `ruff check .` clean, and every task in the Per-Task Verification Map above reports `pass`.
