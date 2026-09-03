---
phase: 10
slug: scheduled-quiet-hours
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-03
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Custom stdlib-only `check(name, fn)` harness convention (no pytest/unittest anywhere in this repo) — every test file defines its own `EXPECTED_CHECK_COUNT` guard and exits non-zero if the actual pass count doesn't match it exactly |
| **Config file** | `pyproject.toml`'s `[tool.coverage.*]` sections (coverage threshold: 83%, `fail_under = 83`); no pytest config exists |
| **Quick run command** | `server/.venv/bin/python3 <harness>.py` (e.g. `server/.venv/bin/python3 server/test_config_history.py`) |
| **Full suite command** | `scripts/run-all-tests.sh` (runs all 16 harnesses under `coverage`, combines, enforces the threshold) |
| **Estimated runtime** | ~30 seconds (single harness) / ~2-3 minutes (full suite with coverage) |

---

## Sampling Rate

- **After every task commit:** Run the single harness touched by that task (e.g. `server/.venv/bin/python3 server/test_config_history.py` after editing `device_config.py`)
- **After every plan wave:** `scripts/run-all-tests.sh` (all 16 harnesses + coverage threshold)
- **Before `/gsd-verify-work`:** Full suite green, plus `server/.venv/bin/python3 -m ruff check .` (blocking lint per CI)
- **Max feedback latency:** ~30 seconds (a single harness run)

---

## Per-Task Verification Map

No requirement IDs are mapped to this phase (unmapped backlog phase promoted from
`SEED-001`). Task IDs are assigned during planning — this table maps each locked
decision to its test coverage per `10-RESEARCH.md`'s Validation Architecture section;
the planner should carry these rows forward into the relevant task's
`<acceptance_criteria>` with concrete Task IDs once plans exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | D-01 (sleep_s extension) | T-06-01-01 (input validation, reused) | Malformed/hostile `quiet_hours_start`/`_end` never reaches `datetime.replace()` uncaught; gated behind `_HHMM_RE.match()` | unit + integration | `server/.venv/bin/python3 stub-server/test_poll_cycle.py` | ✅ (extend existing 23-check harness) | ⬜ pending |
| TBD | TBD | TBD | D-01 (fail-open) | T-06-01-01 | A missing/malformed/hostile `device_config.json` degrades `sleep_s` to the unchanged base value, never raises | unit | same file as above | ✅ | ⬜ pending |
| TBD | TBD | TBD | D-03/D-04 (registry fields) | T-06-01-01 | `normalise_quiet_hours_enabled/start/end()` degrade hostile values to documented defaults; `save_device_config()` rejects invalid submitted values with `ValueError` and leaves the file untouched | unit | `server/.venv/bin/python3 server/test_config_history.py` | ✅ (extend existing 30-check harness) | ⬜ pending |
| TBD | TBD | TBD | D-05 (render once, hold, no re-render) | — | Entering the window renders the quiet-hours canvas exactly once and sets `poll_state["quiet_hours_active"]`; remaining inside the window on a later cycle is a no-op; exiting resumes normal detection next cycle with no transition screen (D-07) | unit + integration | `server/.venv/bin/python3 server/test_poll_loop.py` | ✅ (extend existing 44-check harness) | ⬜ pending |
| TBD | TBD | TBD | D-05/D-06 (screen content) | — | `build_canvas(None, "quiet_hours", quiet_hours_until="07:00")` produces a legal-palette, in-safe-box canvas with the correct heading/body text | unit | `server/.venv/bin/python3 server/test_render.py` | ✅ (extend existing 119-check harness) | ⬜ pending |
| TBD | TBD | TBD | Settings UI (companion fieldset) | T-06-01-01 | New fieldset renders with correct pre-filled values/`checked` state; `handle_post()` validates/rejects malformed HH:MM strings and persists correctly; rendered values pass through `escape_html()` | unit | `server/.venv/bin/python3 companion/test_config_page.py` (run via server venv per `scripts/run-all-tests.sh`) | ✅ (extend existing 64-check harness) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — every harness this phase touches already exists and already has the
`EXPECTED_CHECK_COUNT` convention in place. The only mechanical requirement is
incrementing each touched file's `EXPECTED_CHECK_COUNT` constant by exactly the number
of new `check(...)` calls added in the same commit as the new checks (current counts:
`test_config_history.py` = 30, `test_poll_cycle.py` = 23, `test_poll_loop.py` = 44,
`test_render.py` = 119, `test_config_page.py` = 64).

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Quiet-hours screen visual design (layout/typography/whether it should look distinguishable from the empty state) | D-05/D-06 | `10-CONTEXT.md` and `10-RESEARCH.md` both explicitly defer exact pixel layout to a real-preview review, same discipline `05-CONTEXT.md` used for the battery icon — not mechanically checkable | Render the "quiet_hours" canvas state to a PNG/preview (same method used for `05-CONTEXT.md`'s battery icon), inspect on a real screen or simulated e-ink preview before locking the final layout |
| `<input type="time">` touch-target sizing on the companion Settings page | Settings UI | First `type="time"` input in `companion/static/style.css`; CSS inheritance is a rendering concern, not something the stdlib `check()` harness can assert | Load the companion Settings page in a real browser (desktop + mobile viewport) and confirm the two time inputs inherit the existing `input, select` sizing rule cleanly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
