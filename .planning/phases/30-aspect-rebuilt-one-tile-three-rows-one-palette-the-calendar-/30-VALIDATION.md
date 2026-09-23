---
phase: 30
slug: aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-22
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Custom `check(name, fn)` harnesses (no pytest) — `companion/test_companion_app.py` (string/markup-level), `companion/test_browser_ux.py` (Playwright-driven, real browser) |
| **Config file** | none — each file is a standalone script with a module-level `EXPECTED_CHECK_COUNT` pin and a `main()` returning 0/1 |
| **Quick run command** | `python companion/test_companion_app.py` |
| **Full suite command** | `python scripts/run_all_tests.py` |
| **Estimated runtime** | ~30s quick, several minutes full (browser-driven) |

---

## Sampling Rate

- **After every task commit:** Run `python companion/test_companion_app.py`
- **After every plan wave:** Run `python scripts/run_all_tests.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 30-00-01 | 00 | 0 | CFG-86 | — | N/A | env setup | `pip install -r server/requirements-dev.txt && python -m playwright install chromium` | ❌ W0 | ⬜ pending |
| 30-00-02 | 00 | 0 | CFG-86 | — | N/A | browser | `python companion/test_browser_ux.py` (capture genuine pre-change baseline via `_display_page_height()`) | ✅ (existing instrument, `test_browser_ux.py:2870`) | ⬜ pending |
| 30-XX-01 | TBD | TBD | CFG-85 | — | No-JS control registry holds for every relocated/new control | unit (string-level) | `python companion/test_companion_app.py` | ✅ (existing check, `test_companion_app.py:7172`, registry edited per RESEARCH Pitfall 2) | ⬜ pending |
| 30-XX-02 | TBD | TBD | CFG-85 | — | Palette selection saves with scripts blocked, both languages, 360px | browser | `python companion/test_browser_ux.py` | ⚠️ existing carousel-specific checks (lines 13554-13935) must be rewritten for accordion markup | ⬜ pending |
| 30-XX-03 | TBD | TBD | CFG-85 | — | Every retired CSS rule has no surviving consumer | static grep audit | ad-hoc grep per retired selector, or a small one-off script recorded in the phase SUMMARY | ❌ no existing generic check | ⬜ pending |
| 30-XX-04 | TBD | TBD | CFG-86 | — | Page height at 390px measured before/after, delta reported honestly against the 2600px target | browser | `python companion/test_browser_ux.py` (`_displays_page_height_is_recorded_at_both_phone_widths`) | ✅ existing instrument, guard needs updating per RESEARCH Pitfall 1 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Exact task IDs are assigned by the planner; this map is the requirement→test contract the plan must satisfy, not a literal task list.*

---

## Wave 0 Requirements

- [ ] Install Playwright + Chromium in this worktree (`pip install -r server/requirements-dev.txt && python -m playwright install chromium`) — currently absent, blocks both the CFG-86 measurement and every no-JS browser-level proof this phase needs.
- [ ] Capture a genuine same-instrument "before" page-height reading for CFG-86 against the CURRENT, unmodified tree, before any markup changes land — no historical ROADMAP-cited figure (3743px/3524px/3556px) is a valid substitute for this phase's own baseline.

*No test-file-creation gaps: both harness files already exist and already cover this page; the gap is environment setup and check-rewriting, not missing infrastructure.*

---

## Manual-Only Verifications

*None identified — all phase behaviors (no-JS control contract, scripts-blocked save round trip, page-height measurement, retired-rule consumer audit) have an automated or scriptable verification path per the map above.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (Playwright install, genuine CFG-86 baseline)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
