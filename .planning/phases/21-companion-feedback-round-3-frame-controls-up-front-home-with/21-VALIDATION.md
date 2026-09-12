---
phase: 21
slug: companion-feedback-round-3-frame-controls-up-front-home-with
status: draft
nyquist_compliant: false
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

_Filled by the orchestrator once the plans exist (see the planner output)._

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|

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

- [ ] All tasks have an `<automated>` verify command; none depends on a missing file
- [ ] Sampling continuity: every task runs at least one harness — no three consecutive tasks without automated verification
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20 s per task
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
