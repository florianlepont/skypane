---
phase: 22
slug: companion-audit-round-4-fix-the-blocking-display-save-bar-co
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-12
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `22-RESEARCH.md`'s Validation Architecture section. The per-task map below is filled in by the planner as plans are written; the infrastructure, Wave 0 list and manual-only rows are settled here.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Stdlib-only hand-rolled harnesses (`check(name, fn)` + `EXPECTED_CHECK_COUNT`), no pytest, no unittest. Orchestrated by `scripts/run_all_tests.py` under `coverage run` per file, in parallel, with a repo-wide `fail_under = 83` gate from `pyproject.toml`. This phase adds ONE browser harness alongside them, same conventions. |
| **Config file** | `pyproject.toml` (`[tool.coverage.*]`); `scripts/run_all_tests.py`'s `HARNESSES` list is the discovery config |
| **Quick run command** | `server/.venv/bin/python3 companion/test_config_page.py` (or whichever single harness matches the file just touched — each is a self-contained `main()` with its own exit code) |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Estimated runtime** | Full suite a few tens of seconds; a single harness typically sub-second to a few seconds. The new browser harness adds a browser launch — budget it as the slowest single file and never put it on the per-task path. |

---

## Sampling Rate

- **After every task commit:** run the single harness covering the file(s) touched.
- **After every plan wave:** run `./scripts/run-all-tests.sh`.
- **Before `/gsd:verify-work`:** full suite green, coverage at or above 83 %, and the browser harness having actually run (not skipped) at least once in CI.
- **Max feedback latency:** a few seconds on the per-task path; the browser harness is wave-level only.

---

## Per-Task Verification Map

*Filled in by the planner, one row per task. The requirement-to-test mapping below is settled and must be honoured; only Task ID, Plan and Wave columns are the planner's to assign.*

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|---|---|---|---|---|
| CFG-25 | The save bar appears when a `form=`-attached field changes; the fallback Save stays reachable until the bar is proven live | browser | new browser harness | ❌ W0 |
| CFG-25 | Existing string-comparison assertions for the dirty bar's copy and markup still hold | unit | `companion/test_config_page.py` | ✅ |
| CFG-26 | `next_wake_at_iso()` extends for an active quiet-hours window, evaluated at `last_checkin_ts`, not at render time | unit | `companion/test_view_pages.py` (extend `_wake_next_wake_at_iso_contract`) | ✅ extend |
| CFG-26 | Strip and tile never disagree; no warning inside the grace window | unit | `companion/test_status_pages.py`, `companion/test_view_pages.py` (new assertions against `frame_strip_html`) | ✅ extend |
| CFG-26 | The nightly regression: a frame held through quiet hours is never reported late | unit | new assertion, quiet-hours-active fixture | ❌ W0 fixture |
| CFG-27 | `display_enabled` / `quiet_hours_enabled` resolve to **leave unchanged** when the settings form carries no on/off field (D-12 item 1) | unit | `companion/test_config_page.py` (new `handle_post()` assertions) | ✅ extend |
| CFG-27 | `scope_groups(SCOPE_ALL)` union invariant holds after the registry change (D-12 item 2) | unit | `companion/test_config_page.py::_scope_groups_follow_the_screen_registry` | ✅ pinned |
| CFG-27 | A strip switch does not raise the leave-page dialog with unsaved form edits | browser | new browser harness | ❌ W0 |
| CFG-28 | Battery readout, chart and tooltips render Europe/Paris local time | unit | `companion/test_status_pages.py` (extend the reading-parts assertions) | ✅ extend |
| CFG-28 | Daily battery buckets group by Europe/Paris calendar day across a DST boundary (D-12 item 3) | unit | `server/test_config_history.py` or a new `history_db` test | ❌ W0 fixture |
| CFG-29 | Flash banners, titles, plurals and attribute literals are translated; the scanner sees `app.py` | unit | `companion/test_i18n.py` (widen the scan paths and exception lists) | ✅ extend |
| CFG-30 | Mechanically checkable geometry: runway column count at 390 px, Frame strip cell-height parity, filter Clear on one line | browser | new browser harness, `getBoundingClientRect()` assertions | ❌ W0 |
| CFG-30 | The rest of the pixel-measurement table | manual | see Manual-Only Verifications | — |
| CFG-31 | Mobile nav `hidden` / `aria-expanded` stay consistent through open and close (T5) | browser | new browser harness | ❌ W0 |
| CFG-31 | Cancel restores the form AND the live preview (T8); the leave-guard re-arms on the next edit (T1) | browser | new browser harness | ❌ W0 |
| CFG-31 | Flights detail row expands and collapses with correct ARIA | browser | new browser harness | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 1 of the phase IS Wave 0 of validation: B1 cannot be proven without the harness, and the harness exists because of B1.

- [ ] The browser harness file itself, in `companion/`, following the `check(name, fn)` + `EXPECTED_CHECK_COUNT` convention and reusing `test_companion_app.py`'s `Harness` subprocess pattern (free port, temp state dir, password env var, readiness poll, teardown).
- [ ] A seeded state-directory helper the harness can call, so scenarios run against realistic data rather than an empty install.
- [ ] `server/requirements-dev.txt` — a pinned Playwright line. **Never** `server/requirements.txt`, and never a deployed unit.
- [ ] `.github/workflows/ci.yml` — an install step for the browser. The existing `paths-ignore` docs filter stays as it is.
- [ ] A skip-not-fail path with a clear message when the browser is unavailable, matching how the suite already tolerates the documented macOS Pillow/FreeType digest mismatch.
- [ ] A DST-straddling fixture for the Europe/Paris battery bucketing. No existing test crosses a CET/CEST boundary, so without this the Python rewrite is unproven rather than correct.
- [ ] Quiet-hours-active fixtures for the next-wake contract. The existing pinned test covers screen-on and screen-off only, never a held frame, which is the exact case X2 is about.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| The pixel-measurement table in `22-AUDIT.md` beyond the few geometry facts the browser harness asserts | CFG-30, CFG-31 | The audit's own method was a visual review at two widths in two themes and two languages; reproducing that wholesale is not this harness's job | Re-run the audit's seeded state directory, compare each row of the table at 1280 px and 390 px, light and dark, FR and EN |
| Hover legibility of the segmented control after a click reload (B7) | CFG-30 | A `:hover` state surviving a page load is hard to assert and easy to see | Click FR or EN, leave the pointer still, confirm the label stays readable |
| Real-device rendering: system fonts, address bar, safe-area inset, the new bottom tab bar under a thumb | CFG-30 | Explicitly deferred to phase-level UAT by CONTEXT.md's Deferred Ideas | Open the deployed companion on a real iPhone and Android handset |
| The "within about 5 minutes" screen-off claim (D-04) | CFG-27 | Requires the firmware's real behaviour, not the server's model of it | Switch the screen off on the real frame and time the blank |
| The nightly quiet-hours behaviour in production (X2) | CFG-26 | Inferred from code, never observed live; the unit fixture proves the arithmetic, not the deployment | Watch one real overnight window and confirm no warning state appears |

---

## Validation Sign-Off

- [ ] Every task has an `<automated>` verify or a stated Wave 0 dependency
- [ ] Sampling continuity: no three consecutive tasks without an automated verify
- [ ] Wave 0 covers every ❌ reference above
- [ ] No watch-mode flags
- [ ] Feedback latency within a few seconds on the per-task path
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
